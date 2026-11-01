#!/usr/bin/env python3
"""Build an explicit, pinned HTTPServer HTTP framing compatibility archive."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

SOURCE_SHA256 = '7770a00d22415d58675d2adfafab6504030dea752119acdc9c560593bb8ec978'


def patched_source(source):
    actual = hashlib.sha256(source.encode()).hexdigest()
    if actual != SOURCE_SHA256:
        raise ValueError(f'Unsupported HTTPServer source SHA256 {actual}; review/retest patch against the new version')
    original = '''        Dim body As Bytes = resp.InternalBody()
        Dim useChunked As Boolean = resp.InternalIsChunked()'''
    replacement = '''        Dim body As Bytes = resp.InternalBody()
        Dim isHead As Boolean = False
        If Not ignoreRequest Then
            If Me.mReq <> Nil Then isHead = String.Compare(Me.mReq.Method, "HEAD", True) = 0
        End If
        Dim statusForbidsBody As Boolean = (resp.StatusCode >= 100 And resp.StatusCode < 200) Or resp.StatusCode = 204 Or resp.StatusCode = 304
        Dim noBody As Boolean = isHead Or statusForbidsBody
        Dim useChunked As Boolean = resp.InternalIsChunked() And Not noBody'''
    source = replace_once(source, original, replacement)
    source = replace_once(source, '    Private Sub SendPlainResponse(resp As HttpResponse)',
                          '    Private Sub SendPlainResponse(resp As HttpResponse, ignoreRequest As Boolean = False)')
    # A peer that resets before or during a 4xx answer is a dropped connection,
    # matching upstream RejectUpgrade; an escaping write exception aborts the process.
    source = replace_once(source, '''        Me.mKeepAlive = False
        Me.SendPlainResponse(resp)
        Me.CleanupUploadedFiles()
        Me.Close()
        Me.mPhase = 9''', '''        Me.mKeepAlive = False
        Try
            Me.SendPlainResponse(resp, True)
        Catch writeFailure As Exception
        End Try
        Me.CleanupUploadedFiles()
        Try
            Me.Close()
        Catch closeFailure As Exception
        End Try
        Me.mPhase = 9''')
    source = replace_once(source, '''        Me.SendResponse(resp)
        Me.CleanupUploadedFiles()
        If Not Me.mKeepAlive Then Me.Close()''', '''        If resp.StatusCode >= 100 And resp.StatusCode < 200 Then
            ' An interim status cannot end an exchange (RFC 9110 15.2); answering only 1xx
            ' would pair the next final response with this request on a reused connection.
            resp = New HttpResponse()
            resp.StatusCode = 500
            resp.Write("Internal Server Error")
        End If
        Try
            Me.SendResponse(resp)
        Catch sendFailure As Exception
            Me.mKeepAlive = False
        End Try
        Me.CleanupUploadedFiles()
        If Not Me.mKeepAlive Then
            Try
                Me.Close()
            Catch closeFailure As Exception
            End Try
            ' Closed: never parse requests pipelined behind this one (RFC 9112 9.6).
            Me.mPhase = 9
        End If''')
    # A body that ends inside a file part never adds it to Files; remove its temp file.
    source = replace_once(source, '''    Private Sub FinishMultipartIfAny()
        If Me.mIsMultipart And Me.mMpStream <> Nil Then
            Me.mMpStream.Close()
            Me.mMpStream = Nil
        End If''', '''    Private Sub FinishMultipartIfAny()
        If Me.mIsMultipart And Me.mMpStream <> Nil Then
            Me.mMpStream.Close()
            Me.mMpStream = Nil
            Try
                Dim unfinishedPart As New FileSystemItem(Me.mMpTempPath)
                If unfinishedPart.Exists() Then unfinishedPart.Delete()
            Catch cleanupFailure As Exception
            End Try
        End If''')
    # Wait for the whole delimiter line before closing a part; closing first and
    # rewinding made a delimiter split across reads close the same part twice.
    source = replace_once(source, '''                If delimIdx > 0 Then
                    Me.MultipartWritePartBytes(HttpSlice(Me.mMpBuf, 0, delimIdx))
                End If
                Me.MultipartClosePart()
                Dim afterBoundary2 As Integer = delimIdx + Me.mBoundaryDelim.Count
                Dim lineCrlf2 As Integer = HttpFindCRLF(Me.mMpBuf, afterBoundary2)
                If lineCrlf2 < 0 Then
                    Me.mMpBuf = HttpSlice(Me.mMpBuf, delimIdx, Me.mMpBuf.Count - delimIdx)
                    Return False
                End If''', '''                If delimIdx > 0 Then
                    Me.MultipartWritePartBytes(HttpSlice(Me.mMpBuf, 0, delimIdx))
                    Me.mMpBuf = HttpSlice(Me.mMpBuf, delimIdx, Me.mMpBuf.Count - delimIdx)
                End If
                Dim afterBoundary2 As Integer = Me.mBoundaryDelim.Count
                If Me.mMpBuf.Count >= afterBoundary2 + 2 Then
                    If Me.mMpBuf.Item(afterBoundary2) = 45 And Me.mMpBuf.Item(afterBoundary2 + 1) = 45 Then
                        ' Close delimiter: its trailing CRLF is optional (RFC 2046 5.1.1).
                        Me.MultipartClosePart()
                        Me.mMpPhase = 3
                        Return False
                    End If
                End If
                Dim lineCrlf2 As Integer = HttpFindCRLF(Me.mMpBuf, afterBoundary2)
                If lineCrlf2 < 0 Then
                    ' Bound transport padding like a header line; rescanning is otherwise quadratic.
                    If Me.mMpBuf.Count - afterBoundary2 > Me.Owner.MaxHeaderBytes Then Me.FailAndClose(400)
                    Return False
                End If
                Me.MultipartClosePart()''')
    # A short file read cannot satisfy the sent Content-Length; end the connection.
    source = replace_once(source, '''            Me.Write(readChunk)
            remaining = remaining - readChunk.Count
        Loop
        stream.Close()''', '''            Me.Write(readChunk)
            remaining = remaining - readChunk.Count
        Loop
        stream.Close()
        If remaining > 0 Then Me.mKeepAlive = False''')
    # The multipart parser may FailAndClose mid-body; never dispatch a closed request.
    source = replace_once(source, '''        Me.FeedBodyBytes(bodyChunk)
        If Me.mBodyRemaining = 0 Then''', '''        Me.FeedBodyBytes(bodyChunk)
        If Me.mPhase = 9 Then Return False
        If Me.mBodyRemaining = 0 Then''')
    # Reject malformed escapes before conversion; preserve valid UTF-8 decoding.
    source = replace_once(source, '        If c = "%" And i + 2 < n Then', '        If c = "%" And i + 2 >= n Then Throw New EncodingException("Incomplete percent escape")\n        If c = "%" And i + 2 < n Then')
    source = replace_once(source, """            Else
                outBytes.Append(Bytes.FromString(c, Text.Encodings.UTF8))
                i = i + 1
            End If""", """            Else
                Throw New EncodingException("Invalid percent escape")
            End If""")
    # Parser UTF-8 conversion failures belong to this connection, not the process.
    for method in ('TryParseRequestLine', 'TryParseHeaders', 'TryParseBody'):
        signature = f'    Private Function {method}() As Boolean\n'
        start = source.index(signature) + len(signature)
        end = source.index('    End Function', start)
        body = source[start:end]
        source = source[:start] + '        Try\n' + body + '''        Catch encodingFailure As EncodingException
            Me.FailAndClose(400)
            Return False
        End Try
''' + source[end:]
    source = replace_once(source, '''    Return outBytes.ToString(Text.Encodings.UTF8)
End Function''', '''    For byteIndex As Integer = 0 To outBytes.Count - 1
        If outBytes.Item(byteIndex) = 0 Then Throw New EncodingException("NUL in decoded request target")
    Next
    Return outBytes.ToString(Text.Encodings.UTF8)
End Function''')
    source = replace_once(source, '''    Return HttpSlice(buf, start, length).ToString(Text.Encodings.UTF8)''', '''    Dim slice As Bytes = HttpSlice(buf, start, length)
    For byteIndex As Integer = 0 To slice.Count - 1
        If slice.Item(byteIndex) = 0 Then Throw New EncodingException("NUL in HTTP text")
    Next
    Return slice.ToString(Text.Encodings.UTF8)''')
    source = replace_once(source, '''            Dim nm As String = names(i)
            If String.LCase(nm) = "content-type" Then hasContentType = True''', '''            Dim nm As String = names(i)
            ' Framing belongs to the serializer; never duplicate caller framing.
            If String.LCase(nm) = "content-length" Or String.LCase(nm) = "transfer-encoding" Then Continue For
            If String.LCase(nm) = "content-type" Then hasContentType = True''')
    source = replace_once(source, '''        If useChunked Then
            headerText = headerText + "Transfer-Encoding: chunked\\r\\n"
        Else
            headerText = headerText + "Content-Length: " + String.From(body.Count) + "\\r\\n"
        End If''', '''        If Not statusForbidsBody Then
            If isHead Then
                ' HEAD describes the GET representation, but sends no body.
                Dim headLength As String = resp.InternalHeaderValue("Content-Length").Or(String.From(body.Count))
                ' Only a nonnegative decimal field can enter framing.
                Dim validLength As Boolean = String.Len(headLength) > 0
                For Each digit As String In String.Chars(headLength)
                    If String.IndexOf("0123456789", digit) < 0 Then validLength = False
                Next
                If Not validLength Then headLength = String.From(body.Count)
                headerText = headerText + "Content-Length: " + headLength + "\\r\\n"
            ElseIf useChunked Then
                headerText = headerText + "Transfer-Encoding: chunked\\r\\n"
            Else
                headerText = headerText + "Content-Length: " + String.From(body.Count) + "\\r\\n"
            End If
        End If''')
    source = replace_once(source, '''        Me.Write(headerText)
        If useChunked Then''', '''        Me.Write(headerText)
        If noBody Then Return
        If useChunked Then''')
    source = replace_once(source, '''        If rangeHeader.HasValue Then
            Dim rr As HttpRangeResult''', '''        If rangeHeader.HasValue And String.Compare(Me.mReq.Method, "GET", True) = 0 Then
            Dim rr As HttpRangeResult''')
    source = replace_once(source, '''        stream.Position = rangeStart
        Dim remaining As Integer = contentLen''', '''        If String.Compare(Me.mReq.Method, "HEAD", True) = 0 Then
            stream.Close()
            Return
        End If
        stream.Position = rangeStart
        Dim remaining As Integer = contentLen''')
    source = replace_once(source, '''        If resp.SendFile <> Nil Then
            Me.SendFileResponse(resp)''', '''        If (resp.StatusCode >= 100 And resp.StatusCode < 200) Or resp.StatusCode = 204 Or resp.StatusCode = 304 Then
            Me.SendPlainResponse(resp)
        ElseIf resp.SendFile <> Nil Then
            Me.SendFileResponse(resp)''')
    source = replace_once(source, '''        Dim headerBlock As String = HttpSliceToString(Me.mBuf, 0, endIdx)''', '''        If endIdx > Me.Owner.MaxHeaderBytes Then
            Me.FailAndClose(431)
            Return False
        End If
        Dim headerBlock As String = HttpSliceToString(Me.mBuf, 0, endIdx)''')
    source = replace_once(source, '''            Me.mReq.SetHeader(hName, hValue)''', '''            Dim lowerName As String = String.LCase(hName)
            If lowerName = "content-length" Or lowerName = "transfer-encoding" Then
                If Me.mReq.Header(hName).HasValue Then
                    Me.FailAndClose(400)
                    Return False
                End If
            End If
            Me.mReq.SetHeader(hName, hValue)''')
    source = replace_once(source, '''        Me.mIsMultipart = False''', '''        If transferEncoding.HasValue Then
            If contentLength.HasValue Or String.LCase(transferEncoding.Value) <> "chunked" Then
                Me.FailAndClose(400)
                Return False
            End If
        End If
        If contentLength.HasValue Then
            If String.Len(contentLength.Value) = 0 Then
                Me.FailAndClose(400)
                Return False
            End If
            For Each digit As String In String.Chars(contentLength.Value)
                If String.IndexOf("0123456789", digit) < 0 Then
                    Me.FailAndClose(400)
                    Return False
                End If
            Next
        End If
        Me.mIsMultipart = False''')
    # 1xx framing is already correct; give 100 its registered reason phrase.
    source = replace_once(source, '''    Select Case code
        Case 101
            Return "Switching Protocols"''', '''    Select Case code
        Case 100
            Return "Continue"
        Case 101
            Return "Switching Protocols"''')
    # Every path after a successful open closes the file, including read/write faults.
    declaration = '        Dim stream As BinaryStream = openResult.Value\n'
    start = source.index(declaration, source.index('    Private Sub SendFileResponse')) + len(declaration)
    end = source.index('    End Sub', start)
    body = source[start:end]
    body = body.replace('                    stream.Close()\n', '').replace('            stream.Close()\n', '').replace('        stream.Close()\n', '')
    source = source[:start] + '        Try\n' + body + '        Finally\n            stream.Close()\n        End Try\n' + source[end:]
    return source


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Compatibility patch anchor missing or ambiguous')
    return source.replace(old, new, 1)


def build(package, output, packager='/usr/bin/buoy'):
    with zipfile.ZipFile(package) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        if manifest['name'] != 'HTTPServer' or manifest['version'] != '1.1.0':
            raise ValueError('Only bundled HTTPServer 1.1.0 is supported')
        source = archive.read('modules/HTTPServer.bui').decode()
    patched = patched_source(source)
    with tempfile.TemporaryDirectory(prefix='httpkit-httpserver-compat-') as directory:
        work = Path(directory)
        (work / 'modules').mkdir()
        (work / 'modules/HTTPServer.bui').write_text(patched)
        (work / 'manifest.json').write_text(json.dumps({
            'schema': 1, 'name': 'HTTPServer', 'version': '1.1.0-httpkit.1',
            'description': 'Local HTTPKit compatibility build: explicit response framing and strict request length patch; upstream HTTPServer 1.1.0 source SHA256 ' + SOURCE_SHA256,
        }, indent=2) + '\n')
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([packager, 'pkg', 'seal', str(work), '-o', str(output)], check=True)
    return hashlib.sha256(patched.encode()).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=Path('/usr/share/buoy/packages/HTTPServer-1.1.0.buipkg'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--packager', default='/usr/bin/buoy')
    args = parser.parse_args()
    print('Patched source SHA256:', build(args.package, args.output.resolve(), args.packager))
