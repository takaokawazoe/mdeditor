import base64, quopri
def eml_plain():
    return ("From: Yamada <yamada@example.com>\r\n"
            "To: Suzuki <suzuki@example.com>\r\n"
            "Subject: =?UTF-8?B?" + base64.b64encode('打ち合わせの件'.encode()).decode() + "?=\r\n"
            "Date: Mon, 28 Sep 2026 10:00:00 +0900\r\n"
            "Content-Type: text/plain; charset=UTF-8\r\n"
            "Content-Transfer-Encoding: base64\r\n\r\n"
            + base64.b64encode('お世話になります。\n\n明日の打ち合わせは14時からです。\n\n> 前のメールの引用\n'.encode()).decode() + "\r\n")
def eml_jis():
    body = '件名も本文もISO-2022-JPです。'.encode('iso2022_jp')
    return ("From: old@example.com\r\n"
            "Subject: =?ISO-2022-JP?B?" + base64.b64encode('古いメール'.encode('iso2022_jp')).decode() + "?=\r\n"
            "Content-Type: text/plain; charset=ISO-2022-JP\r\n"
            "Content-Transfer-Encoding: quoted-printable\r\n\r\n"
            + quopri.encodestring(body).decode() + "\r\n")
def eml_multipart():
    return ("From: a@example.com\r\nSubject: multipart test\r\n"
            'Content-Type: multipart/alternative; boundary="BOUND1"\r\n\r\n'
            "--BOUND1\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n"
            "<html><body><p>HTMLの本文</p></body></html>\r\n"
            "--BOUND1\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n"
            "プレーンの本文\r\n--BOUND1--\r\n")
def eml_html_only():
    return ("Subject: html only\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n"
            "<html><body><h1>見出し</h1><p>1行目<br>2行目</p><ul><li>項目</li></ul>"
            "<style>p{color:red}</style>&amp; と &lt;タグ&gt;</body></html>\r\n")
def eml_attach():
    return ("Subject: with attachment\r\n"
            'Content-Type: multipart/mixed; boundary="B2"\r\n\r\n'
            "--B2\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n本文だけ読む\r\n"
            "--B2\r\nContent-Type: application/pdf; name=\"=?UTF-8?B?" + base64.b64encode('資料.pdf'.encode()).decode() + "?=\"\r\n"
            "Content-Disposition: attachment; filename=\"=?UTF-8?B?" + base64.b64encode('資料.pdf'.encode()).decode() + "?=\"\r\n"
            "Content-Transfer-Encoding: base64\r\n\r\nJVBERi0=\r\n--B2--\r\n")
