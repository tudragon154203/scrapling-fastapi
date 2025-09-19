"""Utility for selecting a Gemini API key for GitHub Actions workflows.

This script inspects environment variables named ``GEMINI_API_KEY`` and
optionally ``GEMINI_API_KEY_<n>`` (for example ``GEMINI_API_KEY_2``) to
select a key in a deterministic rotating fashion. The chosen key is appended to
``$GITHUB_ENV`` so that later workflow steps automatically use it. The name of
the environment variable that provided the value is published (without the
secret itself) using ``$GITHUB_OUTPUT`` for auditability.

The rotation seed defaults to standard GitHub Actions run metadata so that
re-runs will advance to the next key. A custom seed can be provided via the
``--seed`` flag or the ``ROTATION_SEED`` environment variable.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class KeyEntry:
    """Holds metadata about a candidate API key."""

    env_name: str
    value: str
    order: Tuple[int, str]


def parse_arguments() -> argparse.Namespace:
    """Configure and parse the command line arguments."""

    parser = argparse.ArgumentParser(
        description="Rotate between Gemini API keys based on a deterministic seed."
    )
    parser.add_argument(
        "--prefix",
        default="GEMINI_API_KEY",
        help="Environment variable prefix that stores the API keys.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Explicit rotation seed. Overrides environment based defaults.",
    )
    parser.add_argument(
        "--export-name",
        default=None,
        help=(
            "Environment variable name that will receive the selected key. "
            "Defaults to the prefix value."
        ),
    )
    parser.add_argument(
        "--output-selected-name",
        default="selected_key_name",
        help=(
            "Name of the GitHub Actions output that records which environment "
            "variable provided the key."
        ),
    )
    parser.add_argument(
        "--presence-output",
        default=None,
        help=(
            "Optional GitHub Actions output that indicates whether any key was "
            "selected."
        ),
    )
    return parser.parse_args()


def gather_candidate_keys(prefix: str) -> List[KeyEntry]:
    """Collect candidate keys from the environment."""

    candidates: List[KeyEntry] = []
    prefix_with_underscore = f"{prefix}_"
    for env_name, value in os.environ.items():
        if env_name == prefix or env_name.startswith(prefix_with_underscore):
            if not value:
                continue
            order_value = derive_order(env_name, prefix)
            candidates.append(
                KeyEntry(env_name=env_name, value=value, order=order_value)
            )
    candidates.sort(key=lambda entry: entry.order)
    return candidates


def derive_order(env_name: str, prefix: str) -> Tuple[int, str]:
    """Return a tuple that ensures consistent ordering of keys."""

    if env_name == prefix:
        return (0, env_name)

    suffix = env_name[len(prefix) + 1 :]
    if suffix.isdigit():
        return (int(suffix), env_name)

    return (10_000, env_name)


def derive_seed(user_seed: Optional[int]) -> int:
    """Determine the rotation seed from arguments or environment variables."""

    if user_seed is not None:
        return user_seed

    env_seed = os.environ.get("ROTATION_SEED")
    if env_seed:
        parsed = parse_seed(env_seed)
        if parsed is not None:
            return parsed

    # Base seed from GitHub run metadata
    base_seed = 0
    for candidate_env in (
        "GITHUB_RUN_ATTEMPT",
        "GITHUB_RUN_NUMBER",
        "GITHUB_RUN_ID",
        "GITHUB_SHA",
    ):
        candidate_value = os.environ.get(candidate_env)
        if not candidate_value:
            continue
        parsed = parse_seed(candidate_value)
        if parsed is not None:
            base_seed = parsed
            break

    # Add job-specific offset
    job_name = os.environ.get("GITHUB_JOB", "")
    if job_name:
        job_hash = parse_seed(job_name)
        base_seed = (base_seed + job_hash) % (2**64)  # Prevent overflow

    # Add random component for each script invocation
    import random
    random.seed(base_seed)
    random_offset = random.randint(0, 1000000)
    return (base_seed + random_offset) % (2**64)


def parse_seed(raw_seed: str) -> Optional[int]:
    """Convert a raw seed value to an integer if possible."""

    try:
        return int(raw_seed)
    except ValueError:
        digest = hashlib.sha256(raw_seed.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big")


def select_key(candidates: Sequence[KeyEntry], seed: int) -> KeyEntry:
    """Select a key based on the provided seed."""

    if not candidates:
        raise RuntimeError("No Gemini API keys were provided via the environment.")
    index = seed % len(candidates)
    return candidates[index]


def mask_value(value: str) -> None:
    """Mask the selected secret so it is not shown in GitHub logs."""

    print(f"::add-mask::{value}")


def append_to_file(file_path: Optional[str], content: str) -> None:
    """Append content to a GitHub Actions file if available."""

    if not file_path:
        print(content)
        return

    with open(file_path, "a", encoding="utf-8") as handle:
        handle.write(f"{content}\n")


def export_selected_key(value: str, export_name: str) -> None:
    """Write the selected key value to the GitHub Actions environment file."""

    github_env = os.environ.get("GITHUB_ENV")
    append_to_file(github_env, f"{export_name}={value}")


def publish_selected_name(output_name: str, selected_env: str) -> None:
    """Publish the selected environment variable name as a workflow output."""

    github_output = os.environ.get("GITHUB_OUTPUT")
    append_to_file(github_output, f"{output_name}={selected_env}")


def publish_presence(output_name: Optional[str], present: bool) -> None:
    """Publish whether any Gemini key was selected."""

    if not output_name:
        return

    github_output = os.environ.get("GITHUB_OUTPUT")
    value = "true" if present else "false"
    append_to_file(github_output, f"{output_name}={value}")


def main() -> None:
    args = parse_arguments()
    prefix: str = args.prefix
    export_name: str = args.export_name or prefix
    presence_output: Optional[str] = args.presence_output

    candidates = gather_candidate_keys(prefix)
    if not candidates:
        publish_presence(presence_output, False)
        if args.allow_missing:
            print(
                "::notice::Skipping Gemini key rotation because no "
                f"{prefix} secrets were provided."
            )
            return

    seed = derive_seed(args.seed)
    selected = select_key(candidates, seed)

    mask_value(selected.value)
    export_selected_key(selected.value, export_name)
    publish_selected_name(args.output_selected_name, selected.env_name)
    publish_presence(presence_output, True)

    print("Selected Gemini key from", selected.env_name, "->", export_name)


if __name__ == "__main__":
    main()
