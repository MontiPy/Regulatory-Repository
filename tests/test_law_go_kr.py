import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIXTURE_HTML = """
<html><body>
  <p class="pty1_p4">
    <input name="joNoList" id="Y000900" type="checkbox"
           value="9:0:000900:111" />
    <span class="bl"><label for="Y000900"> 제9조(최소회전반경) </label></span>
    자동차의 최소회전반경은 12미터를 초과하여서는 아니된다.
  </p>
  <p class="pty1_p2">① 세부기준은 별표와 같다.</p>
  <p class="pty1_p4">
    <input name="joNoList" id="Y001000" type="checkbox"
           value="10:0:001000:222" />
    <span class="bl"><label for="Y001000"> 제10조(접지부분 및 접지압력) </label></span>
    접지부분 및 접지압력은 다음 각호의 기준에 적합하여야 한다.
  </p>
</body></html>
"""

FIXTURE_SUB_HTML = """
<html><body>
  <p class="pty1_p4">
    <input name="joNoList" id="Y001202" type="checkbox"
           value="12의2:0:001202:333" />
    <span class="bl"><label for="Y001202"> 제12조의2(타이어 압력 경보장치) </label></span>
    타이어 압력 경보장치의 기준은 다음과 같다.
  </p>
  <p class="pty1_p4">
    <input name="joNoList" id="Y001300" type="checkbox"
           value="13:0:001300:444" />
    <span class="bl"><label for="Y001300"> 제13조(조종장치) </label></span>
    다음 내용.
  </p>
</body></html>
"""


def test_parse_article_returns_title_and_body():
    from connectors.law_go_kr import _parse_article
    title, body = _parse_article(FIXTURE_HTML, "9")
    assert "제9조" in title
    assert "최소회전반경" in title
    assert "12미터" in body


def test_parse_article_stops_at_next_article():
    from connectors.law_go_kr import _parse_article
    _, body = _parse_article(FIXTURE_HTML, "9")
    assert "접지부분" not in body


def test_parse_article_includes_sub_paragraphs():
    from connectors.law_go_kr import _parse_article
    _, body = _parse_article(FIXTURE_HTML, "9")
    assert "세부기준" in body


def test_parse_sub_article():
    from connectors.law_go_kr import _parse_article
    title, body = _parse_article(FIXTURE_SUB_HTML, "12-2")
    assert "제12조의2" in title
    assert "타이어" in body
    assert "조종장치" not in body


def test_parse_article_missing_returns_fallback():
    from connectors.law_go_kr import _parse_article
    title, body = _parse_article(FIXTURE_HTML, "99")
    assert "99" in title
    assert "See source" in body
