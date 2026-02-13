#!/usr/bin/env python3
"""Analyze extraction results from test_agent.py output."""
import json
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

# All OfficerBio fields the agent could extract (excluding metadata)
BIO_FIELDS = {
    "name":                    {"label": "Name (Chinese)",        "required": True},
    "source_url":              {"label": "Source URL",            "required": True},
    "pinyin_name":             {"label": "Pinyin Name",           "required": False},
    "hometown":                {"label": "Hometown",              "required": False},
    "birth_date":              {"label": "Birth Date",            "required": False},
    "enlistment_date":         {"label": "Enlistment Date",       "required": False},
    "party_membership_date":   {"label": "Party Membership Date", "required": False},
    "retirement_date":         {"label": "Retirement Date",       "required": False},
    "death_date":              {"label": "Death Date",            "required": False},
    "congress_participation":  {"label": "Congress Participation", "required": False},
    "cppcc_participation":     {"label": "CPPCC Participation",   "required": False},
    "promotions":              {"label": "Promotions",            "required": False},
    "notable_positions":       {"label": "Notable Positions",     "required": False},
    "awards":                  {"label": "Awards",                "required": False},
    "wife_name":               {"label": "Wife Name",             "required": False},
}

# Fields that are control variables (expected null for typical obituaries)
CONTROL_FIELDS = {"wife_name", "retirement_date"}

# Ground truth from manual reading of test_obituary.txt
GROUND_TRUTH = {
    "name":                  "林炳尧",
    "hometown":              "福建省晋江市",
    "birth_date":            "1943",
    "enlistment_date":       "1961",
    "party_membership_date": "1964",
    "death_date":            "2023-01-15",
    "promotions":            [{"rank": "少将", "date": "1995"}],
    "notable_positions":     [
        "战士", "班长", "排长", "连长", "营长", "团长",
        "师参谋长", "军参谋长", "某集团军参谋长", "某军区副参谋长",
    ],
    "awards":                ["二级红星功勋荣誉章", "三级独立功勋荣誉章"],
    # Not mentioned in obituary:
    "pinyin_name":            None,
    "congress_participation":  None,
    "cppcc_participation":     None,
    "wife_name":               None,
    "retirement_date":         None,
}


def load_results(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_extraction(bio: dict) -> None:
    console.print(Panel(
        "[bold magenta]1. Extraction Coverage[/bold magenta]",
        border_style="magenta", expand=False,
    ))

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("Field", style="cyan", width=24)
    table.add_column("Extracted", width=36)
    table.add_column("Ground Truth", width=36)
    table.add_column("Verdict", width=10)

    extracted_count = 0
    correct_count = 0
    missed = []
    wrong = []
    correctly_null = []

    for field, meta in BIO_FIELDS.items():
        extracted_val = bio.get(field)
        truth_val = GROUND_TRUTH.get(field)
        label = meta["label"]

        # Format display values
        def fmt(v):
            if v is None:
                return "[dim]null[/dim]"
            if isinstance(v, list):
                if len(v) <= 2:
                    return ", ".join(str(i) if isinstance(i, str) else json.dumps(i, ensure_ascii=False) for i in v)
                return f"{len(v)} items"
            return str(v)

        e_display = fmt(extracted_val)
        t_display = fmt(truth_val)

        # Determine verdict
        if field == "source_url":
            # Provided by caller, not extracted from text
            verdict = "[dim]n/a[/dim]"
        elif truth_val is None and extracted_val is None:
            verdict = "[green]correct[/green]"
            correctly_null.append(label)
        elif truth_val is None and extracted_val is not None:
            verdict = "[yellow]extra[/yellow]"
            wrong.append((label, extracted_val, truth_val))
        elif truth_val is not None and extracted_val is None:
            verdict = "[red]MISSED[/red]"
            missed.append(label)
        else:
            # Both present - compare
            extracted_count += 1
            if isinstance(truth_val, list) and isinstance(extracted_val, list):
                # Compare sets for list fields
                def normalize(lst):
                    return {json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x, dict) else x for x in lst}
                if normalize(truth_val) == normalize(extracted_val):
                    verdict = "[green]correct[/green]"
                    correct_count += 1
                elif normalize(truth_val).issubset(normalize(extracted_val)):
                    verdict = "[green]correct+[/green]"
                    correct_count += 1
                elif normalize(extracted_val).issubset(normalize(truth_val)):
                    verdict = "[yellow]partial[/yellow]"
                    wrong.append((label, extracted_val, truth_val))
                else:
                    verdict = "[yellow]differs[/yellow]"
                    wrong.append((label, extracted_val, truth_val))
            else:
                if str(extracted_val) == str(truth_val):
                    verdict = "[green]correct[/green]"
                    correct_count += 1
                else:
                    verdict = "[yellow]differs[/yellow]"
                    wrong.append((label, extracted_val, truth_val))

        table.add_row(label, e_display, t_display, verdict)

    console.print(table)

    # Summary stats
    total_truth_fields = sum(1 for v in GROUND_TRUTH.values() if v is not None)
    console.print(f"\n  Fields with ground-truth data: [bold]{total_truth_fields}[/bold]")
    console.print(f"  Correctly extracted:           [green]{correct_count}[/green]")
    console.print(f"  Correctly null (control):      [green]{len(correctly_null)}[/green] ({', '.join(correctly_null)})")
    if missed:
        console.print(f"  Missed (present in text):      [red]{len(missed)}[/red] ({', '.join(missed)})")
    else:
        console.print(f"  Missed:                        [green]0[/green]")
    if wrong:
        console.print(f"  Incorrect / partial:           [yellow]{len(wrong)}[/yellow]")
        for label, got, expected in wrong:
            console.print(f"    - {label}: got {got}, expected {expected}")

    accuracy = correct_count / total_truth_fields * 100 if total_truth_fields else 0
    console.print(f"\n  [bold]Extraction accuracy: {accuracy:.0f}% ({correct_count}/{total_truth_fields})[/bold]")


def analyze_tools(tool_calls: list) -> None:
    console.print(Panel(
        "[bold magenta]2. Tool Usage Analysis[/bold magenta]",
        border_style="magenta", expand=False,
    ))

    table = Table(box=box.ROUNDED)
    table.add_column("#", style="dim", width=3)
    table.add_column("Tool", style="cyan", width=28)
    table.add_column("Status", width=8)
    table.add_column("Purpose / Outcome", width=50)

    for i, tc in enumerate(tool_calls, 1):
        name = tc["tool_name"]
        ok = tc["success"]
        status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
        data = tc.get("data", {})

        if name == "lookup_existing_officer":
            purpose = "Check DB for existing record"
            if not ok:
                purpose += f" [dim](DB unavailable)[/dim]"
            elif data.get("found"):
                purpose += " -> found existing"
            else:
                purpose += " -> new officer"
        elif name == "verify_information_present":
            field = data.get("field_name", "?")
            found = data.get("found", False)
            purpose = f"Verify '{field}' in source text -> {'found' if found else 'not found'}"
        elif name == "validate_dates":
            warnings_list = data.get("warnings", [])
            checked = data.get("checked", {})
            n_promos = checked.get("promotion_count", 0)
            purpose = f"Chronological check ({n_promos} promotion(s))"
            if warnings_list:
                purpose += f", {len(warnings_list)} warning(s)"
            else:
                purpose += " -> all consistent"
        elif name == "save_officer_bio":
            purpose = "Persist validated bio"
            if ok:
                score = data.get("confidence_score", "?")
                rid = data.get("record_id")
                purpose += f" (confidence={score}"
                if rid:
                    purpose += f", DB id={rid}"
                purpose += ")"
        else:
            purpose = tc.get("error", "")[:50] if not ok else str(data)[:50]

        table.add_row(str(i), name, status, purpose)

    console.print(table)

    # Stats
    total = len(tool_calls)
    ok_count = sum(1 for tc in tool_calls if tc["success"])
    console.print(f"\n  Total tool calls: {total}")
    console.print(f"  Succeeded: [green]{ok_count}[/green], Failed: [red]{total - ok_count}[/red]")
    console.print(f"  Success rate: [bold]{ok_count/total*100:.0f}%[/bold]")

    # Which tools were most useful?
    console.print("\n  [bold]Most useful tools:[/bold]")
    if any(tc["tool_name"] == "validate_dates" and tc["success"] for tc in tool_calls):
        console.print("    [green]validate_dates[/green] - caught/confirmed date consistency")
    if any(tc["tool_name"] == "verify_information_present" and tc["success"] for tc in tool_calls):
        console.print("    [green]verify_information_present[/green] - prevented hallucination on missing fields")
    if any(tc["tool_name"] == "save_officer_bio" and tc["success"] for tc in tool_calls):
        console.print("    [green]save_officer_bio[/green] - validated schema + persisted data")

    # Underused tools
    used_names = {tc["tool_name"] for tc in tool_calls}
    all_tools = {"lookup_existing_officer", "verify_information_present",
                 "validate_dates", "save_officer_bio", "lookup_unit_by_name"}
    unused = all_tools - used_names
    if unused:
        console.print(f"\n  [bold]Unused tools:[/bold] {', '.join(unused)}")


def analyze_validation(tool_calls: list, bio: dict) -> None:
    console.print(Panel(
        "[bold magenta]3. Validation Effectiveness[/bold magenta]",
        border_style="magenta", expand=False,
    ))

    checks = []

    # Did agent validate dates?
    date_calls = [tc for tc in tool_calls if tc["tool_name"] == "validate_dates"]
    if date_calls:
        tc = date_calls[0]
        if tc["success"]:
            checked = tc["data"].get("checked", {})
            checks.append(("[green]PASS[/green]", "Date validation",
                           f"Checked {len(checked)} date fields, all consistent"))
        else:
            checks.append(("[red]FAIL[/red]", "Date validation", tc.get("error", "unknown")))
    else:
        checks.append(("[red]SKIP[/red]", "Date validation", "Agent never called validate_dates"))

    # Did agent verify control fields?
    verify_calls = [tc for tc in tool_calls if tc["tool_name"] == "verify_information_present"]
    verified_fields = [tc["data"].get("field_name") for tc in verify_calls if tc["success"]]
    if verified_fields:
        checks.append(("[green]PASS[/green]", "Control field verification",
                       f"Verified: {', '.join(verified_fields)}"))
    else:
        checks.append(("[yellow]WEAK[/yellow]", "Control field verification",
                       "No verify_information_present calls for control fields"))

    # Did agent check for congress/cppcc before leaving null?
    congress_verified = "congress_participation" in verified_fields
    cppcc_verified = "cppcc_participation" in verified_fields
    if not congress_verified and bio.get("congress_participation") is None:
        checks.append(("[yellow]WEAK[/yellow]", "Congress participation",
                       "Left null without verifying against source text"))
    if not cppcc_verified and bio.get("cppcc_participation") is None:
        checks.append(("[yellow]WEAK[/yellow]", "CPPCC participation",
                       "Left null without verifying against source text"))

    # Did save succeed on first attempt?
    save_calls = [tc for tc in tool_calls if tc["tool_name"] == "save_officer_bio"]
    if len(save_calls) == 1 and save_calls[0]["success"]:
        checks.append(("[green]PASS[/green]", "First-attempt save",
                       "save_officer_bio succeeded on first call (no retries needed)"))
    elif len(save_calls) > 1:
        ok = sum(1 for s in save_calls if s["success"])
        checks.append(("[yellow]RETRY[/yellow]", "Save attempts",
                       f"{len(save_calls)} attempts, {ok} succeeded"))
    elif not save_calls:
        checks.append(("[red]FAIL[/red]", "Save", "Agent never called save_officer_bio"))

    # Confidence score sanity
    score = bio.get("confidence_score", 0)
    if 0.8 <= score <= 1.0:
        checks.append(("[green]PASS[/green]", "Confidence score",
                       f"{score} - reasonable for well-structured obituary"))
    elif score < 0.5:
        checks.append(("[yellow]LOW[/yellow]", "Confidence score",
                       f"{score} - unusually low, agent may be uncertain"))
    else:
        checks.append(("[green]OK[/green]", "Confidence score", str(score)))

    table = Table(box=box.ROUNDED)
    table.add_column("Status", width=8)
    table.add_column("Check", style="cyan", width=28)
    table.add_column("Detail", width=55)
    for status, check, detail in checks:
        table.add_row(status, check, detail)
    console.print(table)


def suggest_improvements(bio: dict, tool_calls: list) -> None:
    console.print(Panel(
        "[bold magenta]4. Suggested Improvements[/bold magenta]",
        border_style="magenta", expand=False,
    ))

    suggestions = []

    # Check for missing pinyin
    if bio.get("pinyin_name") is None:
        suggestions.append((
            "System Prompt",
            "Add pinyin generation instruction",
            "The agent did not produce a pinyin_name. Add to the system prompt: "
            "\"If pinyin is not in the text, transliterate the Chinese name yourself "
            "and include it as pinyin_name.\"",
        ))

    # Check if verify_information_present was underused
    verify_calls = [tc for tc in tool_calls if tc["tool_name"] == "verify_information_present"]
    verified_fields = {tc["data"].get("field_name") for tc in verify_calls}
    ideal_verify = {"wife_name", "congress_participation", "cppcc_participation", "retirement_date"}
    missing_verify = ideal_verify - verified_fields
    if missing_verify:
        suggestions.append((
            "System Prompt",
            "Require verification of all control/null fields",
            f"Agent only verified {verified_fields or 'none'} but should also check: "
            f"{', '.join(missing_verify)}. Add: \"Before setting any field to null, "
            f"call verify_information_present to confirm it is truly absent.\"",
        ))

    # Check if lookup_unit_by_name was never used
    used_tools = {tc["tool_name"] for tc in tool_calls}
    if "lookup_unit_by_name" not in used_tools:
        suggestions.append((
            "System Prompt",
            "Encourage unit lookups for promotions",
            "The agent never called lookup_unit_by_name. If the DB had unit data, "
            "linking promotions to unit IDs would improve data quality. Add: "
            "\"When extracting promotions, use lookup_unit_by_name to resolve unit references.\"",
        ))

    # Check if only one promotion was extracted when text lists 少将
    promos = bio.get("promotions", [])
    if len(promos) == 1:
        suggestions.append((
            "Tool / Schema",
            "Infer implicit promotions from position progression",
            "Only 1 explicit promotion (少将 1995) was extracted, but the career "
            "progression (战士 -> 班长 -> ... -> 军参谋长) implies earlier rank changes. "
            "Consider adding a tool or prompt instruction to infer intermediate promotions "
            "from the position history.",
        ))

    # Token efficiency
    # (loaded from top-level data in main)

    # DB persistence
    save_calls = [tc for tc in tool_calls if tc["tool_name"] == "save_officer_bio"]
    if save_calls and save_calls[0].get("data", {}).get("record_id") is None:
        suggestions.append((
            "Infrastructure",
            "Fix database permissions for pla_leaders table",
            "save_officer_bio validated successfully but could not write to the DB "
            "(table missing or permission denied). Run initialize_database() with a "
            "privileged user, or grant CREATE on the public schema to the app user.",
        ))

    # Print
    if not suggestions:
        console.print("  [green]No improvements needed - extraction looks solid![/green]")
        return

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("Area", style="cyan", width=16)
    table.add_column("Suggestion", style="bold", width=36)
    table.add_column("Detail", width=50)
    for area, title, detail in suggestions:
        table.add_row(area, title, detail)
    console.print(table)


def main():
    result_path = Path(__file__).parent / "output" / "test_extraction.json"
    if not result_path.exists():
        console.print(f"[red]Result file not found: {result_path}[/red]")
        console.print("Run test_agent.py first to generate extraction results.")
        return 1

    data = load_results(result_path)
    bio = data.get("officer_bio", {})
    tool_calls = data.get("tool_calls", [])

    console.print(Panel.fit(
        "[bold magenta]PLA Agent SDK - Extraction Analysis[/bold magenta]\n"
        f"Officer: {bio.get('name', '?')}  |  "
        f"Success: {data.get('success')}  |  "
        f"Turns: {data.get('conversation_turns')}  |  "
        f"Tokens: {data.get('total_input_tokens', 0) + data.get('total_output_tokens', 0):,}",
        border_style="magenta",
    ))

    analyze_extraction(bio)
    console.print()
    analyze_tools(tool_calls)
    console.print()
    analyze_validation(tool_calls, bio)
    console.print()
    suggest_improvements(bio, tool_calls)
    console.print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
