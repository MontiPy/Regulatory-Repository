"""Shared fixtures for the regulatory-repository test suite."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


SAMPLE_ECFR_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <DIV8 N="108" TYPE="SECTION">
      <HEAD>§ 571.108   Lamps, reflective devices, and associated equipment.</HEAD>
      <P>Each vehicle shall comply with § 571.108(a).</P>
      <P>The requirements of this section apply to all motor vehicles.</P>
      <CITA>[49 FR 28964, July 17, 1984]</CITA>
    </DIV8>
""")

SAMPLE_EGOV_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <Law>
      <LawBody>
        <LawTitle>道路運送車両の保安基準</LawTitle>
        <MainProvision>
          <Article Num="11">
            <ArticleCaption>後写鏡等</ArticleCaption>
            <Paragraph>
              <ParagraphSentence>自動車には、後写鏡を備えなければならない。</ParagraphSentence>
            </Paragraph>
          </Article>
          <Article Num="11_2">
            <ArticleCaption>間接視界装置</ArticleCaption>
            <Paragraph>
              <ParagraphSentence>自動車には、間接視界装置を備えることができる。</ParagraphSentence>
            </Paragraph>
          </Article>
          <Article Num="22">
            <ArticleCaption>車枠及び車体</ArticleCaption>
            <Paragraph>
              <ParagraphSentence>自動車の車枠及び車体は、堅ろうなものでなければならない。</ParagraphSentence>
            </Paragraph>
          </Article>
        </MainProvision>
      </LawBody>
    </Law>
""")

SAMPLE_CA_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <Regulations>
      <LongTitle>Motor Vehicle Safety Regulations</LongTitle>
      <Section>
        <Label>108</Label>
        <TitleText>Lighting Systems and Reflective Devices</TitleText>
        <Subsection>
          <Label>108(1)</Label>
          <Text>Every vehicle shall be equipped with the required lamps.</Text>
        </Subsection>
      </Section>
      <Section>
        <Label>209</Label>
        <TitleText>Seat Belt Assemblies</TitleText>
        <Subsection>
          <Label>209(1)</Label>
          <Text>Every seat belt assembly shall meet the requirements of this section.</Text>
        </Subsection>
      </Section>
    </Regulations>
""")


@pytest.fixture
def ecfr_xml() -> str:
    return SAMPLE_ECFR_XML


@pytest.fixture
def egov_xml() -> str:
    return SAMPLE_EGOV_XML


@pytest.fixture
def ca_xml() -> str:
    return SAMPLE_CA_XML


@pytest.fixture
def tmp_regulations_dir(tmp_path: Path) -> Path:
    return tmp_path / "regulations"
