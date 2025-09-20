"""Abstract base class for API key rotation utilities.

This module provides a common framework for rotating API keys in GitHub Actions
workflows. Concrete implementations should inherit from BaseKeyRotator and
override the abstract methods to provider-specific behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class KeyEntry:
    """Holds metadata about a candidate API key."""

    env_name: str
    value: str
    order: Tuple[int, str]


class BaseKeyRotator(ABC):
    """Abstract base class for API key rotation."""

    def __init__(self) -> None:
        """Initialize the key rotator."""
        pass

    @property
    @abstractmethod
    def default_prefix(self) -> str:
        """Return the default environment variable prefix for this API provider."""
        pass

    @property
    @abstractmethod
    def error_message(self) -> str:
        """Return the error message when no keys are found."""
        pass

    @property
    @abstractmethod
    def success_message(self) -> str:
        """Return the success message format for key selection."""
        pass

    def _get_additional_arguments(self) -> List[argparse.Action]:
        """Return any additional command line arguments for this implementation.
        
        Returns:
            List of argparse actions to add to the parser.
        """
        return []

    def parse_arguments(self) -> argparse.Namespace:
        """Configure and parse the command line arguments."""
        parser = argparse.ArgumentParser(
            description=f"Rotate between {self.__class__.__name__} API keys based on a deterministic seed."
        )
        parser.add_argument(
            "--prefix",
            default=self.default_prefix,
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
        
        # Add any additional arguments from the concrete implementation
        for args, kwargs in self._get_additional_arguments():
            parser.add_argument(*args, **kwargs)
            
        return parser.parse_args()

    def gather_candidate_keys(self, prefix: str) -> List[KeyEntry]:
        """Collect candidate keys from the environment."""
        candidates: List[KeyEntry] = []
        prefix_with_underscore = f"{prefix}_"
        for env_name, value in os.environ.items():
            if env_name == prefix or env_name.startswith(prefix_with_underscore):
                if not value:
                    continue
                order_value = self.derive_order(env_name, prefix)
                candidates.append(
                    KeyEntry(env_name=env_name, value=value, order=order_value)
                )
        candidates.sort(key=lambda entry: entry.order)
        return candidates

    def derive_order(self, env_name: str, prefix: str) -> Tuple[int, str]:
        """Return a tuple that ensures consistent ordering of keys."""
        if env_name == prefix:
            return (0, env_name)

        suffix = env_name[len(prefix) + 1 :]
        if suffix.isdigit():
            return (int(suffix), env_name)

        return (10_000, env_name)

    def derive_seed(self, user_seed: Optional[int]) -> int:
        """Determine the rotation seed from arguments or environment variables."""
        if user_seed is not None:
            return user_seed

        env_seed = os.environ.get("ROTATION_SEED")
        if env_seed:
            parsed = self.parse_seed(env_seed)
            if parsed is not None:
                return parsed

        # Base seed from GitHub run metadata
        modulus = 2**64
        base_seed = 0
        for candidate_env in (
            "GITHUB_RUN_ID",
            "GITHUB_RUN_NUMBER",
            "GITHUB_SHA",
        ):
            candidate_value = os.environ.get(candidate_env)
            if not candidate_value:
                continue
            candidate_seed = self.parse_seed(candidate_value)
            base_seed = (base_seed + candidate_seed) % modulus

        # Mix in the run attempt so retries within a run can select different keys
        attempt_value = os.environ.get("GITHUB_RUN_ATTEMPT")
        if attempt_value:
            attempt_seed = self.parse_seed(attempt_value)
            base_seed = (base_seed + attempt_seed) % modulus

        # Add workflow-specific entropy so different workflows avoid sharing seeds
        workflow_name = os.environ.get("GITHUB_WORKFLOW", "")
        if workflow_name:
            workflow_hash = self.parse_seed(workflow_name)
            base_seed = (base_seed + workflow_hash) % modulus

        # Add job-specific offset
        job_name = os.environ.get("GITHUB_JOB", "")
        if job_name:
            job_hash = self.parse_seed(job_name)
            base_seed = (base_seed + job_hash) % modulus  # Prevent overflow

        # Add random component for each script invocation
        random.seed(base_seed)
        random_offset = random.randint(0, 1000000)
        return (base_seed + random_offset) % modulus

    def parse_seed(self, raw_seed: str) -> Optional[int]:
        """Convert a raw seed value to an integer if possible."""
        try:
            return int(raw_seed)
        except ValueError:
            digest = hashlib.sha256(raw_seed.encode("utf-8")).digest()
            return int.from_bytes(digest[:8], "big")

    def select_key(self, candidates: Sequence[KeyEntry], seed: int) -> KeyEntry:
        """Select a key based on the provided seed."""
        if not candidates:
            raise RuntimeError(self.error_message)
        index = seed % len(candidates)
        return candidates[index]

    def mask_value(self, value: str) -> None:
        """Mask the selected secret so it is not shown in GitHub logs."""
        print(f"::add-mask::{value}")

    def append_to_file(self, file_path: Optional[str], content: str) -> None:
        """Append content to a GitHub Actions file if available."""
        if not file_path:
            print(content)
            return

        with open(file_path, "a", encoding="utf-8") as handle:
            handle.write(f"{content}\n")

    def export_selected_key(self, value: str, export_name: str) -> None:
        """Write the selected key value to the GitHub Actions environment file."""
        github_env = os.environ.get("GITHUB_ENV")
        self.append_to_file(github_env, f"{export_name}={value}")

    def publish_selected_name(self, output_name: str, selected_env: str) -> None:
        """Publish the selected environment variable name as a workflow output."""
        github_output = os.environ.get("GITHUB_OUTPUT")
        self.append_to_file(github_output, f"{output_name}={selected_env}")

    def publish_presence(self, output_name: Optional[str], present: bool) -> None:
        """Publish whether any key was selected."""
        if not output_name:
            return

        github_output = os.environ.get("GITHUB_OUTPUT")
        value = "true" if present else "false"
        self.append_to_file(github_output, f"{output_name}={value}")

    def run(self) -> None:
        """Execute the key rotation process."""
        args = self.parse_arguments()
        prefix: str = args.prefix
        export_name: str = args.export_name or prefix

        candidates = self.gather_candidate_keys(prefix)
        if not candidates:
            raise RuntimeError(self.error_message)

        seed = self.derive_seed(args.seed)
        selected = self.select_key(candidates, seed)

        self.mask_value(selected.value)
        self.export_selected_key(selected.value, export_name)
        self.publish_selected_name(args.output_selected_name, selected.env_name)
        self.publish_presence("key_present", True)
        
        print(self.success_message.format(selected.env_name, export_name))