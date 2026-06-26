"""週次レポート生成（Google Docs 出力）。

  python weekly_report.py            # 直近 WEEKLY_REPORT_DAYS 日のレポートをDocsに作成
  python weekly_report.py --days 7   # 期間指定
  python weekly_report.py --no-notify  # Gmail通知しない

フロー: Sheets読込 → カテゴリ集計 → Gemini要約/気づき → Docs作成 → (任意)Gmail通知
"""
import argparse
import logging
import sys
from datetime import datetime

from config import REPORT_TITLE_PREFIX, WEEKLY_REPORT_DAYS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("screenlog.weekly")


def _fmt_minutes(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    return f"{h}h{m:02d}m" if h else f"{m}m"


def build_insights_prompt(agg: dict) -> str:
    """集計結果から Gemini への要約・気づき生成プロンプトを組み立てる。"""
    cat_lines = "\n".join(
        f"  - {c['category']}: {_fmt_minutes(c['minutes'])} ({c['percent']}%, {c['count']}件)"
        for c in agg["by_category"]
    ) or "  (データなし)"
    recent = "\n".join(f"  - {s}" for s in agg["recent_summaries"][:15]) or "  (なし)"
    return (
        "あなたは業務改善コンサルタントです。以下はPC作業ログの週次集計です。\n"
        "日本語で、(1)今週の傾向の要約 (2)気づき・改善提案 を簡潔な箇条書きでまとめてください。\n"
        "誇張せず事実ベースで。機密情報は出力しないこと。\n\n"
        f"## 期間: 直近{agg['period_days']}日 / 記録数: {agg['record_count']}件 / "
        f"合計: {_fmt_minutes(agg['total_minutes'])}\n\n"
        f"## カテゴリ別内訳\n{cat_lines}\n\n"
        f"## 直近の作業要約\n{recent}\n"
    )


def build_report_text(agg: dict, ai_insights: str, now: datetime) -> str:
    """Docs に書き込むレポート本文（プレーンテキスト）を組み立てる。"""
    lines = [
        f"{REPORT_TITLE_PREFIX}  {now.strftime('%Y-%m-%d')}",
        "",
        f"期間: 直近{agg['period_days']}日",
        f"記録数: {agg['record_count']}件",
        f"合計作業時間: {_fmt_minutes(agg['total_minutes'])}",
        "",
        "■ カテゴリ別内訳",
    ]
    if agg["by_category"]:
        for c in agg["by_category"]:
            lines.append(
                f"  {c['category']}: {_fmt_minutes(c['minutes'])} "
                f"({c['percent']}%, {c['count']}件)"
            )
    else:
        lines.append("  (データなし)")
    lines += ["", "■ AIによる要約・気づき", ai_insights or "(生成なし)", ""]
    return "\n".join(lines)


def generate_weekly_report(days: int, notify: bool = True) -> tuple[str, str]:
    """週次レポートを生成し Docs に書き出す。(doc_url, report_text) を返す。"""
    from report_reader import aggregate_rows, read_rows
    from analyzer import generate_text
    from docs_writer import create_report_doc

    now = datetime.now()
    rows = read_rows()
    agg = aggregate_rows(rows, now=now, days=days)
    log.info("集計: %d件 / %s", agg["record_count"], _fmt_minutes(agg["total_minutes"]))

    ai_insights = ""
    if agg["record_count"] > 0:
        try:
            ai_insights = generate_text(build_insights_prompt(agg))
        except Exception as e:  # noqa: BLE001
            log.warning("Gemini要約に失敗（集計のみで継続）: %s", e)

    report_text = build_report_text(agg, ai_insights, now)
    title = f"{REPORT_TITLE_PREFIX} {now.strftime('%Y-%m-%d')}"
    _, url = create_report_doc(title, report_text)

    if notify:
        from gmail_notifier import send_notification

        send_notification(
            subject=f"[ScreenLog] 週次レポート {now.strftime('%Y-%m-%d')}",
            body=f"週次レポートを作成しました。\n\n{url}\n\n"
            f"記録数: {agg['record_count']}件 / 合計: {_fmt_minutes(agg['total_minutes'])}",
        )

    return url, report_text


def main() -> int:
    parser = argparse.ArgumentParser(description="ScreenLog 週次レポート (Docs)")
    parser.add_argument("--days", type=int, default=WEEKLY_REPORT_DAYS, help="集計期間（日）")
    parser.add_argument("--no-notify", action="store_true", help="Gmail通知しない")
    args = parser.parse_args()

    try:
        url, _ = generate_weekly_report(days=args.days, notify=not args.no_notify)
    except Exception as e:  # noqa: BLE001
        log.error("週次レポート生成に失敗: %s", e)
        return 1
    print(f"レポート: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
