"""Check source-level journal requirements and agreed editorial constraints.

These checks do not certify authorship, plagiarism, visual pagination or acceptance.
"""
from pathlib import Path
import hashlib, json, re, unicodedata
HERE = Path(__file__).resolve().parent
s = (HERE/"main.tex").read_text()
body = s.split(r"\begin{document}",1)[1]
citations = [k for group in re.findall(r"\\cite\{([^}]+)\}",s) for k in group.split(",")]
entries = re.findall(r"\\bibitem\{([^}]+)\}([^\n]+)",s)
keys = [k for k,_ in entries]
authors = [unicodedata.normalize("NFKD",v.strip().split(",")[0]).encode("ascii","ignore").decode().casefold() for _,v in entries]
abstracts = re.findall(r"\\item\[\](.*?)\\vspace\{10pt\}",s,re.S)
assert len(abstracts)==2, "Bilingual abstracts must be present"
en_words = len(re.findall(r"\b[\w]+(?:[-'][\w]+)*\b",abstracts[0]))
zh_chars = len(re.findall(r"[\u4e00-\u9fff]",abstracts[1]))
labels = re.findall(r"\\label\{([^}]+)\}",s)
refs = re.findall(r"\\(?:eqref|ref)\{([^}]+)\}",s)
checks = {
    "cited_references_only_no_count_quota": set(citations)==set(keys) and len(keys)==len(set(keys)) and bool(keys),
    "alphabetic_reference_order": authors==sorted(authors),
    "abstracts_within_500_words_or_Han_characters": en_words<=500 and zh_chars<=500,
    "separate_bilingual_abstract_pages": s.count(r"\clearpage")==2 and r"\textbf{Key words:}" in s and r"\textbf{關鍵詞：}" in s,
    "a4_geometry_preserved": r"\documentclass[a4paper,10pt]{article}" in s and "top=3.5cm,bottom=2cm,left=2cm,right=2cm" in s,
    "body_9pt_1p5_line_spacing_preserved": r"\fontsize{9}{13.5}" in s,
    "two_column_body": r"\begin{multicols}{2}" in s,
    "heading_depth_at_most_three": not re.search(r"\\(?:paragraph|subparagraph)\{",s),
    "labels_unique_and_references_resolved": len(labels)==len(set(labels)) and set(refs)<=set(labels),
    "no_manuscript_placeholders": not re.search(r"\b(?:TODO|TBD|PLACEHOLDER|Lorem ipsum)\b",body,re.I),
    "no_authorship_detector_claim": not re.search(r"100% human|AI[- ]free|undetectable|zero AI",body,re.I),
    "historical_results_separate": "retrospective results" in s and "simplified proxy" in s and "ID-corrected" in s,
}
report = dict(source_sha256=hashlib.sha256(s.encode()).hexdigest(),
    status="PASS" if all(checks.values()) else "FAIL",checks=checks,
    reference_count=len(keys),english_abstract_words=en_words,chinese_abstract_Han_characters=zh_chars,
    requirements_sources=["https://jo.dyu.edu.tw/setjournal/contribute.htm",
        "https://jo.dyu.edu.tw/setjournal/document/jour04-1.pdf"],
    editorial_policy="Prioritize method, results and interpretation; cite only sources serving the argument. Do not fabricate evidence or certify non-AI authorship.",
    manual_checks_remaining=[
        "Final visual pagination and table widths; native compilation alone does not verify these.",
        "Complete author postal addresses, Chinese affiliations and contact telephone.",
        "Regenerate and review the required Word submission files after source approval.",
        "Formal evidence-snapshot admission; historical original execution bindings remain incomplete."
    ])
(HERE/"editorial-checks.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
assert all(checks.values()), "Source-level editorial checks failed"

