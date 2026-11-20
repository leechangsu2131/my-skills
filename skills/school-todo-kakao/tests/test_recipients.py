from schooltodo import recipients as rcp


def _rows():
    return [
        {"_row": 2, "이름": "", "받기": "매일", "카카오ID": "111", "uuid": ""},
        {"_row": 3, "이름": "엄마", "받기": "주간출장", "카카오ID": "222", "uuid": "U2"},
        {"_row": 4, "이름": "", "받기": "주간출장", "카카오ID": "333", "uuid": ""},
        {"_row": 5, "이름": "쉬는 사람", "받기": "", "카카오ID": "444", "uuid": ""},
    ]


def test_needs_lookup_ignores_rows_without_kind():
    rows = _rows()
    assert rcp.needs_lookup(rows)
    assert not rcp.needs_lookup([rows[1], rows[3]])


def test_fill_from_friends_matches_by_id_and_reports_cells():
    rows = _rows()
    friends = [{"id": "111", "uuid": "U1", "name": "동료"}, {"id": "999", "uuid": "U9", "name": "남"}]
    changes = rcp.fill_from_friends(rows, friends)
    assert (2, "uuid", "U1") in changes and (2, "이름", "동료") in changes
    assert len(changes) == 2
    assert rows[0]["uuid"] == "U1" and rows[2]["uuid"] == ""


def test_targets_waiting_merge_batches():
    rows = _rows()
    rcp.fill_from_friends(rows, [{"id": "111", "uuid": "U1", "name": "동료"}])
    assert rcp.targets(rows, rcp.KIND_DAILY) == ["U1"]
    assert rcp.targets(rows, rcp.KIND_WEEKLY) == ["U2"]
    assert rcp.waiting(rows, rcp.KIND_WEEKLY) == 1
    assert rcp.merge(["A", "B"], ["B", "C"]) == ["A", "B", "C"]
    assert rcp.batches(list("abcdefg")) == [list("abcde"), list("fg")]


class FakeWs:
    def __init__(self, vals):
        self.vals = vals
        self.updates = None

    def get_all_values(self):
        return self.vals

    def batch_update(self, cells, value_input_option=None):
        self.updates = (cells, value_input_option)


def test_sheet_reads_by_header_and_writes_raw_cells():
    ws = FakeWs([["받기", "이름", "카카오ID", "uuid"], ["매일", "", "111", ""], ["", "", "", ""]])
    sheet = rcp.RecipientSheet(ws)
    rows = sheet.rows()
    assert len(rows) == 1 and rows[0]["_row"] == 2
    sheet.write(rcp.fill_from_friends(rows, [{"id": "111", "uuid": "U1", "name": "동료"}]))
    cells, opt = ws.updates
    assert {"range": "D2", "values": [["U1"]]} in cells and {"range": "B2", "values": [["동료"]]} in cells
    assert opt == "RAW"


def test_view_link_and_share_tab_upsert():
    from schooltodo.recipients import ShareTab, view_link

    assert view_link("https://x/exec", "T", "daily") == "https://x/exec?view=T&k=daily"
    ws = FakeWs([["WEBAPP_URL", "https://x/exec"], ["VIEW_TOKEN", "T"]])
    tab = ShareTab(ws)
    assert tab.values()["VIEW_TOKEN"] == "T"
    tab.save({"VIEW_TOKEN": "T2", "DAILY_TEXT": "본문"})
    cells, opt = ws.updates
    assert {"range": "A2:B2", "values": [["VIEW_TOKEN", "T2"]]} in cells
    assert {"range": "A3:B3", "values": [["DAILY_TEXT", "본문"]]} in cells and opt == "RAW"
