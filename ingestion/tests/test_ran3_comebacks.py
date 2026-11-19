import docx

from ingestion.ran3_comebacks import Comeback, keep_removed, link_folders, match_folder, parse_comebacks
from docx.shared import RGBColor


def _doc(tmp_path, lines):
    d = docx.Document()
    for kind, text, *opt in lines:
        if kind == "h":
            d.add_heading(text, level=2)
        else:
            r = d.add_paragraph().add_run(text)
            r.font.color.rgb = RGBColor(0xFF, 0x00, 0xFF) if kind == "pink" else RGBColor(0, 0, 0)
            if opt and opt[0] == "strike":
                r.font.strike = True
    p = tmp_path / "n.docx"
    d.save(p)
    return str(p)


def test_open_closed_and_skips(tmp_path):
    path = _doc(tmp_path, [
        ("h", "2.5. Additional reminders"), ("pink", "CB: # 1_Name"),
        ("h", "9.1. LTE"), ("pink", "CB: # 2_R19PSCellinfo"),
        ("h", "9.2. NR"), ("pink", "# 3_R19UEperfm"), ("black", "# 4_NotACB"),
        ("h", "10.5.1. AI/ML use cases"), ("pink", "CB: # 6GAIML1_Usecase"),
        ("pink", "CB: # 99_Withdrawn", "strike"),
    ])
    got = {c.name: (c.agendaCode, c.status, c.number) for c in parse_comebacks(path)}
    assert got == {
        "R19PSCellinfo": ("9.1", "open", "2"),
        "R19UEperfm": ("9.2", "closed", "3"),
        "6GAIML1_Usecase": ("10.5.1", "open", None),
    }


def test_folder_number_mismatch_links_by_name():
    rows = [Comeback(name="R20_SON&MDT_Intra-CULTM", agendaCode="11.2.2", status="open")]
    assert match_folder("CB # 17_R20_SON&MDT_Intra-CULTM", rows)["agendaCode"] == "11.2.2"


def test_ambiguous_folder_stays_unlinked():
    rows = [Comeback(name="X_A", agendaCode="9.1", status="open"), Comeback(name="XA", agendaCode="9.2", status="open")]
    assert match_folder("CB # X_A", rows) is None
    assert link_folders(rows, ["CB # X_A"])[0] == ["CB # X_A"]


def test_removed_comeback_keeps_agenda():
    out = keep_removed([], [{"name": "R19UEperfm", "agendaCode": "9.2", "folder": "CB # 3_R19UEperfm"}])
    assert (out[0].status, out[0].agendaCode) == ("removed", "9.2")
