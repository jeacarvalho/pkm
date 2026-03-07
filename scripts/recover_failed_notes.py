#!/usr/bin/env python3
"""
Error recovery script for notes that consistently fail topic classification.
This script:
1. Shows notes that have failed multiple times
2. Allows manual review and retry
3. Provides options to skip permanently or force retry
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import frontmatter
import argparse
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.topics.daily_sync import DailySync


def load_failure_tracker() -> Dict[str, Any]:
    """Load failure tracker data."""
    tracker_file = (
        project_root
        / "data"
        / "logs"
        / "topics"
        / "daily_sync"
        / "failure_tracker.json"
    )

    if tracker_file.exists():
        try:
            with open(tracker_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading failure tracker: {e}")
            return {}
    return {}


def get_notes_with_failures(
    tracker_data: Dict[str, Any], min_failures: int = 3
) -> List[Dict[str, Any]]:
    """Get notes with at least min_failures."""
    failed_notes = []

    for note_path, data in tracker_data.items():
        failures = data.get("failures", 0)
        last_failure = data.get("last_failure")
        skipped_until = data.get("skipped_until")

        if failures >= min_failures:
            # Check if still skipped
            is_skipped = False
            if skipped_until:
                try:
                    skipped_date = datetime.fromisoformat(skipped_until)
                    if datetime.now() < skipped_date:
                        is_skipped = True
                except:
                    pass

            failed_notes.append(
                {
                    "path": note_path,
                    "failures": failures,
                    "last_failure": last_failure,
                    "skipped_until": skipped_until,
                    "is_skipped": is_skipped,
                }
            )

    # Sort by failure count (descending)
    failed_notes.sort(key=lambda x: x["failures"], reverse=True)
    return failed_notes


def show_note_content(note_path: str) -> None:
    """Show note content for manual review."""
    vault_dir = Path("/home/s015533607/MEGAsync/Minhas_notas")
    full_path = vault_dir / note_path

    if not full_path.exists():
        print(f"Note not found: {full_path}")
        return

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        post = frontmatter.loads(content)

        print(f"\n{'=' * 80}")
        print(f"NOTE: {note_path}")
        print(f"{'=' * 80}")

        # Show metadata
        print("\nMETADATA:")
        for key, value in post.metadata.items():
            if key == "topic_classification":
                print(
                    f"  {key}: [TOPICS PRESENT - {len(value) if isinstance(value, list) else '?'} topics]"
                )
            else:
                print(f"  {key}: {value}")

        # Show first 500 characters of content
        print(f"\nCONTENT (first 500 chars):")
        content_preview = post.content[:500]
        if len(post.content) > 500:
            content_preview += "..."
        print(content_preview)

        # Show file stats
        file_size = full_path.stat().st_size
        print(f"\nFILE STATS:")
        print(f"  Size: {file_size} bytes")
        print(f"  Lines: {len(post.content.splitlines())}")

    except Exception as e:
        print(f"Error reading note: {e}")


def retry_note(note_path: str) -> bool:
    """Retry processing a single note."""
    vault_dir = Path("/home/s015533607/MEGAsync/Minhas_notas")
    full_path = vault_dir / note_path

    if not full_path.exists():
        print(f"Note not found: {full_path}")
        return False

    try:
        # Import here to avoid circular imports
        from src.topics.topic_extractor import TopicExtractor
        from src.topics.config import Config

        config = Config()
        extractor = TopicExtractor(config)

        print(f"\nRetrying note: {note_path}")

        # Process the note
        result = extractor.process_note(str(full_path))

        if result and "topics" in result:
            print(f"✅ Success! Extracted {len(result['topics'])} topics")
            return True
        else:
            print(f"❌ Failed to extract topics")
            return False

    except Exception as e:
        print(f"❌ Error during retry: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Recover failed notes")
    parser.add_argument(
        "--min-failures",
        type=int,
        default=3,
        help="Minimum failures to show (default: 3)",
    )
    parser.add_argument(
        "--list", action="store_true", help="List failed notes without interactive mode"
    )
    parser.add_argument(
        "--retry", type=str, help="Retry a specific note (provide path)"
    )
    parser.add_argument(
        "--retry-all", action="store_true", help="Retry all failed notes"
    )
    parser.add_argument("--clear-skip", type=str, help="Clear skip status for a note")

    args = parser.parse_args()

    # Load failure tracker
    tracker_data = load_failure_tracker()

    if args.retry:
        # Retry specific note
        success = retry_note(args.retry)
        sys.exit(0 if success else 1)

    elif args.retry_all:
        # Retry all failed notes
        failed_notes = get_notes_with_failures(tracker_data, args.min_failures)

        if not failed_notes:
            print("No failed notes found.")
            return

        print(f"Retrying {len(failed_notes)} failed notes...")

        success_count = 0
        for note_info in failed_notes:
            note_path = note_info["path"]
            print(f"\n[{success_count + 1}/{len(failed_notes)}] {note_path}")

            if retry_note(note_path):
                success_count += 1

        print(f"\n✅ Successfully retried {success_count}/{len(failed_notes)} notes")
        sys.exit(0)

    elif args.clear_skip:
        # Clear skip status
        if args.clear_skip in tracker_data:
            if "skipped_until" in tracker_data[args.clear_skip]:
                del tracker_data[args.clear_skip]["skipped_until"]
                print(f"Cleared skip status for: {args.clear_skip}")

                # Save updated tracker
                tracker_file = (
                    project_root
                    / "data"
                    / "logs"
                    / "topics"
                    / "daily_sync"
                    / "failure_tracker.json"
                )
                tracker_file.parent.mkdir(parents=True, exist_ok=True)
                with open(tracker_file, "w", encoding="utf-8") as f:
                    json.dump(tracker_data, f, indent=2, ensure_ascii=False)
            else:
                print(f"Note not currently skipped: {args.clear_skip}")
        else:
            print(f"Note not in tracker: {args.clear_skip}")
        sys.exit(0)

    else:
        # Interactive mode or list mode
        failed_notes = get_notes_with_failures(tracker_data, args.min_failures)

        if not failed_notes:
            print("No failed notes found.")
            return

        print(f"\n📊 FAILED NOTES SUMMARY")
        print(f"Total notes with ≥{args.min_failures} failures: {len(failed_notes)}")
        print(f"{'=' * 80}")

        for i, note_info in enumerate(failed_notes, 1):
            status = "⏸️ SKIPPED" if note_info["is_skipped"] else "❌ FAILING"
            print(f"{i:3d}. {status} {note_info['path']}")
            print(
                f"     Failures: {note_info['failures']}, Last: {note_info['last_failure']}"
            )
            if note_info["skipped_until"]:
                print(f"     Skipped until: {note_info['skipped_until']}")

        if args.list:
            return

        # Interactive mode
        print(f"\n{'=' * 80}")
        print("INTERACTIVE MODE")
        print("Commands:")
        print("  [number] - Show note content")
        print("  r[number] - Retry note")
        print("  s[number] - Skip note permanently (add to ignore list)")
        print("  c[number] - Clear skip status")
        print("  q - Quit")
        print("  a - Retry all")
        print(f"{'=' * 80}")

        while True:
            try:
                cmd = input("\nCommand: ").strip().lower()

                if cmd == "q":
                    break
                elif cmd == "a":
                    # Retry all
                    confirm = input("Retry all failed notes? (y/N): ").strip().lower()
                    if confirm == "y":
                        success_count = 0
                        for note_info in failed_notes:
                            if retry_note(note_info["path"]):
                                success_count += 1
                        print(
                            f"✅ Successfully retried {success_count}/{len(failed_notes)} notes"
                        )
                    continue

                # Parse command with number
                if cmd and cmd[0].isalpha() and cmd[1:].isdigit():
                    action = cmd[0]
                    num = int(cmd[1:]) - 1

                    if 0 <= num < len(failed_notes):
                        note_info = failed_notes[num]
                        note_path = note_info["path"]

                        if action == "r":  # Retry
                            retry_note(note_path)
                        elif action == "s":  # Skip permanently
                            confirm = (
                                input(f"Skip {note_path} permanently? (y/N): ")
                                .strip()
                                .lower()
                            )
                            if confirm == "y":
                                # Add to ignore list
                                ignore_file = (
                                    project_root
                                    / "data"
                                    / "logs"
                                    / "topics"
                                    / "daily_sync"
                                    / "ignore_list.txt"
                                )
                                ignore_file.parent.mkdir(parents=True, exist_ok=True)

                                with open(ignore_file, "a", encoding="utf-8") as f:
                                    f.write(f"{note_path}\n")
                                print(f"✅ Added {note_path} to ignore list")
                        elif action == "c":  # Clear skip
                            if note_info["is_skipped"]:
                                # Clear skip status in tracker
                                if (
                                    note_path in tracker_data
                                    and "skipped_until" in tracker_data[note_path]
                                ):
                                    del tracker_data[note_path]["skipped_until"]

                                    # Save updated tracker
                                    tracker_file = (
                                        project_root
                                        / "data"
                                        / "logs"
                                        / "topics"
                                        / "daily_sync"
                                        / "failure_tracker.json"
                                    )
                                    with open(tracker_file, "w", encoding="utf-8") as f:
                                        json.dump(
                                            tracker_data,
                                            f,
                                            indent=2,
                                            ensure_ascii=False,
                                        )

                                    print(f"✅ Cleared skip status for {note_path}")
                                else:
                                    print(f"Note not currently skipped: {note_path}")
                            else:
                                print(f"Note not currently skipped: {note_path}")
                        else:
                            print(f"Unknown action: {action}")
                    else:
                        print(f"Invalid note number: {num + 1}")

                elif cmd.isdigit():
                    num = int(cmd) - 1
                    if 0 <= num < len(failed_notes):
                        show_note_content(failed_notes[num]["path"])
                    else:
                        print(f"Invalid note number: {num + 1}")

                else:
                    print("Invalid command")

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    main()
