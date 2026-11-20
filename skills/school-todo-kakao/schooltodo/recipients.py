"""'받는사람' 탭: 카카오톡 '친구에게 보내기'로 알림을 받을 가족·친한 동료.

  열: 이름 | 받기 | 카카오ID | uuid | 등록시각   (열 이름으로 읽는다)
  - 받는 사람이 등록 링크(챗봇 웹앱 ?join=daily|weekly)로 카카오 동의를 하면 챗봇이 카카오ID·받기를 적는다.
  - uuid는 '보내는 사람 기준' 값이라 챗봇은 모른다. 아침 실행이 선생님 친구 목록에서 카카오ID로 찾아 이름·uuid를 채운다.
  - 받기: '매일' = 아침 일정 메시지, '주간출장' = 주 1회 출장 메시지. 비우면 보내지 않는다.
"""
from __future__ import annotations

KIND_DAILY = "매일"
KIND_WEEKLY = "주간출장"
HEAD = ["이름", "받기", "카카오ID", "uuid", "등록시각"]
BATCH = 5  # 카카오 '친구에게 보내기' 한 번에 최대 5명
DAILY_QUOTA = 30  # 심사 전 앱 전체 하루 친구 발송 한도


def needs_lookup(rows: list[dict]) -> bool:
    """카카오ID는 있는데 uuid나 이름이 빈 행이 있으면 친구 목록을 조회해야 한다."""
    return any(r.get("카카오ID") and (not r.get("uuid") or not r.get("이름")) for r in rows if r.get("받기"))


def fill_from_friends(rows: list[dict], friends: list[dict]) -> list[tuple[int, str, str]]:
    """빈 uuid·이름을 친구 목록(id로 대조)에서 채운다. rows도 고친다. 바꿀 칸 목록 [(행번호, 열이름, 값)]을 돌려준다."""
    by_id = {str(f.get("id", "")): f for f in friends if f.get("id")}
    changes = []
    for r in rows:
        f = by_id.get(str(r.get("카카오ID", "")).strip())
        if not f:
            continue
        if not r.get("uuid") and f.get("uuid"):
            r["uuid"] = f["uuid"]
            changes.append((r["_row"], "uuid", f["uuid"]))
        if not r.get("이름") and f.get("name"):
            r["이름"] = f["name"]
            changes.append((r["_row"], "이름", f["name"]))
    return changes


def targets(rows: list[dict], kind: str) -> list[str]:
    return [r["uuid"] for r in rows if r.get("받기") == kind and r.get("uuid")]


def waiting(rows: list[dict], kind: str) -> int:
    """등록은 됐지만 아직 친구 목록에서 찾지 못한(uuid 없음) 사람 수."""
    return sum(1 for r in rows if r.get("받기") == kind and not r.get("uuid"))


def merge(*lists: list[str]) -> list[str]:
    out: list[str] = []
    for lst in lists:
        for u in lst:
            if u and u not in out:
                out.append(u)
    return out


def batches(uuids: list[str], n: int = BATCH) -> list[list[str]]:
    return [uuids[i : i + n] for i in range(0, len(uuids), n)]


class ShareTab:
    """'공유링크' 탭(A=이름, B=값): 버튼으로 여는 읽기 전용 페이지(챗봇 웹앱 ?view=)에 필요한 값.
    VIEW_TOKEN(추측 못 하는 주소용 비밀값), WEBAPP_URL(챗봇 웹앱 /exec 주소), DAILY_TEXT·WEEKLY_TEXT(페이지 본문), UPDATED."""

    def __init__(self, worksheet):
        self._ws = worksheet

    def values(self) -> dict[str, str]:
        return {r[0].strip(): (r[1] if len(r) > 1 else "") for r in self._ws.get_all_values() if r and r[0].strip()}

    def save(self, updates: dict[str, str]) -> None:
        cur = self._ws.get_all_values()
        keys = [r[0].strip() if r else "" for r in cur]
        cells, nxt = [], len(cur) + 1
        for k, v in updates.items():
            if k in keys:
                row = keys.index(k) + 1
            else:
                row, nxt = nxt, nxt + 1
            cells.append({"range": f"A{row}:B{row}", "values": [[k, v]]})
        if cells:
            self._ws.batch_update(cells, value_input_option="RAW")


def view_link(base_url: str, token: str, kind: str) -> str:
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}view={token}&k={kind}"


class RecipientSheet:
    def __init__(self, worksheet):
        self._ws = worksheet
        self._head: list[str] = []

    def rows(self) -> list[dict]:
        vals = self._ws.get_all_values()
        if not vals:
            return []
        self._head = [h.strip() for h in vals[0]]
        out = []
        for i, row in enumerate(vals[1:], start=2):
            row = row + [""] * (len(self._head) - len(row))
            rec = {h: str(v).strip() for h, v in zip(self._head, row)}
            if rec.get("카카오ID") or rec.get("uuid"):
                rec["_row"] = i
                out.append(rec)
        return out

    def write(self, changes: list[tuple[int, str, str]]) -> None:
        if not changes:
            return
        import gspread.utils

        cells = []
        for row, name, value in changes:
            if name in self._head:
                a1 = gspread.utils.rowcol_to_a1(row, self._head.index(name) + 1)
                cells.append({"range": a1, "values": [[value]]})
        if cells:
            self._ws.batch_update(cells, value_input_option="RAW")
