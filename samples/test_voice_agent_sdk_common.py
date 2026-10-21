"""Offline tests for the preview Voice Agent SDK sample helpers."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from voice_agent_definition import materialize_handoff_instruction_inheritance
from voice_agent_sdk_common import (
    EventPrinter,
    _canonical_definition,
    _load_settings,
    _realtime_url,
    _validate_agent_name,
    _validate_project_endpoint,
    load_materialized_agent,
)


class VoiceAgentSdkCommonTests(unittest.TestCase):
    def test_materializes_shared_handoff_instructions_for_publish(self) -> None:
        definition = {
            "instructions": "Shared policy.",
            "handoff": {
                "nodes": [
                    {
                        "id": "billing",
                        "config": {
                            "instructions": "Handle billing.",
                            "inherit_from_base_instructions": True,
                        },
                    },
                    {
                        "id": "support",
                        "config": {
                            "instructions": "Handle support.",
                            "inherit_from_base_instructions": False,
                        },
                    },
                ],
                "edges": [],
            },
        }

        materialize_handoff_instruction_inheritance(definition)

        billing = definition["handoff"]["nodes"][0]["config"]
        support = definition["handoff"]["nodes"][1]["config"]
        self.assertEqual(
            "Shared policy.\n\nHandle billing.",
            billing["instructions"],
        )
        self.assertEqual("Handle support.", support["instructions"])
        self.assertNotIn("inherit_from_base_instructions", billing)
        self.assertNotIn("inherit_from_base_instructions", support)

    def test_validates_project_endpoint_and_agent_name(self) -> None:
        endpoint = "https://account.services.ai.azure.com/api/projects/project"
        self.assertEqual(_validate_project_endpoint(endpoint + "/"), endpoint)
        self.assertEqual(_validate_agent_name("sdk-sample-agent"), "sdk-sample-agent")

        with self.assertRaises(ValueError):
            _validate_project_endpoint("https://<account>/api/projects/<project>")
        with self.assertRaises(ValueError):
            _validate_project_endpoint("https://evil.example/api/projects/stolen")
        with self.assertRaises(ValueError):
            _validate_project_endpoint(
                "https://account.services.ai.azure.com.evil.example/api/projects/stolen"
            )
        with self.assertRaises(ValueError):
            _validate_agent_name("invalid agent name")

    def test_materializes_each_sample_without_environment_leakage(self) -> None:
        template = {
            "name": "template-name",
            "description": "test",
            "definition": {
                "kind": "voice",
                "model_type": "managed",
                "model": "default-model",
                "tools": [
                    {
                        "type": "mcp",
                        "server_label": "tools",
                        "server_url": "",
                        "project_connection_id": "",
                    }
                ],
            },
        }
        environments = [
            (
                "first-agent",
                "first-model",
                "https://first.example/mcp",
                "first-connection",
            ),
            (
                "second-agent",
                "second-model",
                "https://second.example/mcp",
                "second-connection",
            ),
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample_dirs = []
            for index, values in enumerate(environments):
                agent_name, model, server_url, connection_id = values
                sample_dir = root / str(index)
                sample_dir.mkdir()
                (sample_dir / "agent.json").write_text(
                    json.dumps(template),
                    encoding="utf-8",
                )
                (sample_dir / ".env").write_text(
                    "\n".join(
                        [
                            "AZURE_AI_PROJECT_ENDPOINT="
                            "https://account.services.ai.azure.com/api/projects/project",
                            f"VOICE_AGENT_NAME={agent_name}",
                            f"VOICE_AGENT_MODEL={model}",
                            f"VOICE_AGENT_MCP_SERVER_URL={server_url}",
                            f"VOICE_AGENT_MCP_CONNECTION_ID={connection_id}",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
                sample_dirs.append(sample_dir)

            with patch.dict(os.environ, {}, clear=True):
                first_name, _, first = load_materialized_agent(sample_dirs[0])
                second_name, _, second = load_materialized_agent(sample_dirs[1])

        self.assertEqual(first_name, "first-agent")
        self.assertEqual(second_name, "second-agent")
        self.assertEqual(first["model_type"], "managed")
        self.assertEqual(second["model_type"], "managed")
        self.assertEqual(first["model"], "first-model")
        self.assertEqual(second["model"], "second-model")
        self.assertEqual(
            first["tools"][0]["project_connection_id"],
            "first-connection",
        )
        self.assertEqual(
            second["tools"][0]["project_connection_id"],
            "second-connection",
        )

    def test_mcp_config_switch_overrides_sample_mcp_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sample_dir = Path(directory)
            config_dir = sample_dir / "config"
            config_dir.mkdir()
            (config_dir / "shared.env").write_text(
                "\n".join(
                    [
                        "VOICE_AGENT_MCP_SERVER_URL="
                        "https://shared.example/mcp/finance",
                        "VOICE_AGENT_MCP_CONNECTION_ID=shared-connection",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (sample_dir / ".env").write_text(
                "\n".join(
                    [
                        "AZURE_AI_PROJECT_ENDPOINT="
                        "https://account.services.ai.azure.com/api/projects/project",
                        "VOICE_AGENT_MCP_CONFIG=config/shared.env",
                        "VOICE_AGENT_MCP_SERVER_URL=https://internal.example/mcp",
                        "VOICE_AGENT_MCP_CONNECTION_ID=internal-connection",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                settings = _load_settings(sample_dir)

        self.assertEqual(
            settings["VOICE_AGENT_MCP_SERVER_URL"],
            "https://shared.example/mcp/finance",
        )
        self.assertEqual(
            settings["VOICE_AGENT_MCP_CONNECTION_ID"],
            "shared-connection",
        )

    def test_mcp_config_switch_reports_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sample_dir = Path(directory)
            (sample_dir / ".env").write_text(
                "VOICE_AGENT_MCP_CONFIG=missing.env\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "VOICE_AGENT_MCP_CONFIG does not exist",
                ):
                    _load_settings(sample_dir)

    def test_canonicalizes_service_audio_defaults(self) -> None:
        authored = {
            "audio": {
                "input": {
                    "turn_detection": {
                        "remove_filler_words": False,
                    }
                },
                "output": {
                    "voice": "en-US-AvaNeural",
                    "voice_type": "azure-standard",
                },
            }
        }
        readback = {
            "audio": {
                "input": {"turn_detection": {}},
                "output": {
                    "voice": {
                        "type": "azure-standard",
                        "name": "en-US-AvaNeural",
                    }
                },
            }
        }
        self.assertEqual(
            _canonical_definition(authored),
            _canonical_definition(readback),
        )

    def test_builds_encoded_realtime_url(self) -> None:
        url = _realtime_url(
            "https://account.services.ai.azure.com/api/projects/project",
            "sample-agent",
            "session-id",
        )
        self.assertEqual(
            url,
            "wss://account.services.ai.azure.com/api/projects/project/"
            "agents/sample-agent/endpoint/protocols/voice"
            "?api-version=v1&agent_session_id=session-id",
        )

    def test_committed_directory_scenarios_match_expected_shapes(self) -> None:
        samples = Path(__file__).resolve().parent
        common_settings = {
            "AZURE_AI_PROJECT_ENDPOINT": (
                "https://account.services.ai.azure.com/api/projects/project"
            ),
            "AZURE_CREDENTIAL_MODE": "default",
            "VOICE_AGENT_MODEL": "gpt-realtime",
            "VOICE_AGENT_MCP_SERVER_URL": "https://tools.example/mcp",
        }
        _, _, finance = load_materialized_agent(
            samples / "example1_finance_with_handoff_realtime",
            {
                **common_settings,
                "VOICE_AGENT_NAME": "finance-test",
                "VOICE_AGENT_MCP_CONNECTION_ID": "finance-connection",
            },
        )
        _, _, otp_officer_search = load_materialized_agent(
            samples / "example2_finance_with_OTP_and_Officer_Search",
            {
                **common_settings,
                "VOICE_AGENT_NAME": "finance-otp-officer-search-test",
                "VOICE_AGENT_MCP_CONNECTION_ID": "finance-otp-officer-search-connection",
            },
        )
        _, _, elevator_service = load_materialized_agent(
            samples / "example3_elevator_service_with_safety_zendesk_and_handoff",
            {
                **common_settings,
                "VOICE_AGENT_NAME": "elevator-service-test",
                "VOICE_AGENT_MCP_CONNECTION_ID": "elevator-service-connection",
            },
        )


        self.assertEqual(finance["model_type"], "managed")
        self.assertEqual(finance["model"], "gpt-realtime")
        self.assertEqual(len(finance["handoff"]["nodes"]), 13)
        self.assertEqual(len(finance["handoff"]["edges"]), 24)

        self.assertEqual(otp_officer_search["model_type"], "managed")
        self.assertEqual(otp_officer_search["model"], "gpt-realtime")
        self.assertNotIn("handoff", otp_officer_search)
        self.assertEqual(
            otp_officer_search["tools"][0]["allowed_tools"],
            [
                "verify_caller_otp",
                "calculate_loan_offer",
                "record_loan_interest",
                "auto_assign_loan_officer",
                "search_loan_officer",
                "confirm_loan_officer",
                "end_call",
            ],
        )
        self.assertEqual(elevator_service["model_type"], "managed")
        self.assertEqual(elevator_service["model"], "gpt-realtime")
        self.assertEqual(
            "en-US-Ava:DragonHDLatestNeural",
            elevator_service["audio"]["output"]["voice"]["name"],
        )
        self.assertEqual(
            "azure-standard",
            elevator_service["audio"]["output"]["voice"]["type"],
        )
        self.assertEqual(len(elevator_service["handoff"]["nodes"]), 9)
        self.assertEqual(len(elevator_service["handoff"]["edges"]), 17)
        source_definition = json.loads(
            (
                samples
                / "example3_elevator_service_with_safety_zendesk_and_handoff"
                / "agent.json"
            ).read_text(encoding="utf-8")
        )["definition"]
        shared_instructions = source_definition["instructions"]
        self.assertIn("## CONVERSATIONAL RESPONSE", shared_instructions)
        self.assertIn(
            "Match an explicitly stated emotion with restrained empathy.",
            shared_instructions,
        )
        self.assertIn(
            "that operation is the only next step",
            shared_instructions,
        )
        self.assertIn(
            "Never invent or\nintensify an emotion",
            shared_instructions,
        )
        self.assertNotIn("## CURRENT NODE", shared_instructions)
        for source_node, materialized_node in zip(
            source_definition["handoff"]["nodes"],
            elevator_service["handoff"]["nodes"],
            strict=True,
        ):
            source_config = source_node["config"]
            materialized_config = materialized_node["config"]
            self.assertIs(source_config["inherit_from_base_instructions"], True)
            self.assertTrue(
                source_config["instructions"].startswith("## CURRENT NODE\n")
            )
            self.assertNotIn("## GLOBAL POLICY", source_config["instructions"])
            self.assertNotIn(
                "inherit_from_base_instructions",
                materialized_config,
            )
            self.assertTrue(
                materialized_config["instructions"].startswith("## GLOBAL POLICY\n")
            )
            self.assertIn(
                "\n\n## CURRENT NODE\n",
                materialized_config["instructions"],
            )
        query_edge = next(
            edge
            for edge in elevator_service["handoff"]["edges"]
            if edge["id"] == "intent_router_to_query_issue"
        )
        self.assertEqual("auto", query_edge["target_response"])
        self.assertEqual(
            "I understand you want a clear update on this ticket.",
            query_edge["transfer_message"],
        )
        report_issue = next(
            node
            for node in elevator_service["handoff"]["nodes"]
            if node["id"] == "report_issue"
        )
        self.assertEqual(
            [
                "record_issue",
                "assess_safety",
                "mock_zendesk_create_ticket",
            ],
            report_issue["config"]["tools"][0]["allowed_tools"],
        )
        query_issue = next(
            node
            for node in elevator_service["handoff"]["nodes"]
            if node["id"] == "query_issue"
        )
        self.assertEqual(
            ["mock_zendesk_get_ticket_status"],
            query_issue["config"]["tools"][0]["allowed_tools"],
        )
        self.assertIsNone(query_issue["config"]["interim_response"])
        human_handoff = next(
            node
            for node in elevator_service["handoff"]["nodes"]
            if node["id"] == "human_handoff"
        )
        self.assertEqual(
            ["request_human_handoff"],
            human_handoff["config"]["tools"][0]["allowed_tools"],
        )
        self.assertNotIn(
            "transfer_call",
            {
                tool.get("name")
                for node in elevator_service["handoff"]["nodes"]
                for tool in node["config"]["tools"]
            },
        )

    def test_example1_directories_preserve_original_workflow_and_runtime(self) -> None:
        samples = Path(__file__).resolve().parent
        settings = {
            "AZURE_AI_PROJECT_ENDPOINT": (
                "https://account.services.ai.azure.com/api/projects/project"
            ),
            "AZURE_CREDENTIAL_MODE": "default",
            "VOICE_AGENT_NAME": "stale-env-agent",
            "VOICE_AGENT_MODEL": "stale-env-model",
            "VOICE_AGENT_MCP_SERVER_URL": "https://tools.example/mcp",
            "VOICE_AGENT_MCP_CONNECTION_ID": "finance-connection",
        }
        with patch.dict(os.environ, {}, clear=True):
            realtime_name, _, realtime = load_materialized_agent(
                samples / "example1_finance_with_handoff_realtime",
                settings,
                prefer_document_name=True,
            )
            cascade_name, _, cascade = load_materialized_agent(
                samples / "example1_finance_with_handoff_cascade",
                settings,
                prefer_document_name=True,
            )
            # The reviewed speech-only defaults were replaced by the revised
            # candidates and remain selectable as a backup version.
            previous = "backups/20261021T064258Z/previous_default/agent.json"
            _, _, previous_realtime = load_materialized_agent(
                samples / "example1_finance_with_handoff_realtime",
                settings,
                agent_file=previous,
                prefer_document_name=True,
            )
            _, _, previous_cascade = load_materialized_agent(
                samples / "example1_finance_with_handoff_cascade",
                settings,
                agent_file=previous,
                prefer_document_name=True,
            )

        self.assertEqual("finance-example-realtime", realtime_name)
        self.assertEqual("finance-example-cascade-luna", cascade_name)
        for definition in (realtime, cascade):
            self.assertEqual(13, len(definition["handoff"]["nodes"]))
            self.assertEqual(24, len(definition["handoff"]["edges"]))
        self.assertEqual(
            [(edge["source"], edge["target"]) for edge in realtime["handoff"]["edges"]],
            [(edge["source"], edge["target"]) for edge in cascade["handoff"]["edges"]],
        )
        self.assertEqual(previous_realtime["handoff"], previous_cascade["handoff"])
        self.assertEqual(previous_realtime["greeting"], previous_cascade["greeting"])
        self.assertEqual(
            {
                "type": "template",
                "text": (
                    "Hello, this is Virtual Finance calling "
                    "about a personal loan offer."
                ),
            },
            previous_realtime["greeting"],
        )
        edges = {
            edge["id"]: edge for edge in previous_realtime["handoff"]["edges"]
        }
        for edge_id in (
            "entrypoint_to_dial_assess",
            "dial_assess_to_rpc",
            "ivr_to_rpc",
            "rpc_to_offer",
            "offer_to_offer_decision",
            "appointment_to_offer_summary",
        ):
            with self.subTest(edge=edge_id):
                self.assertNotIn("transfer_message", edges[edge_id])
                self.assertEqual("auto", edges[edge_id]["target_response"])
        self.assertEqual(
            {
                "dial_assess_to_voicemail": (
                    "A calling assistant tried to reach you and will try again later."
                ),
                "ivr_to_voicemail": (
                    "A calling assistant tried to reach you and will try again later."
                ),
                "offer_decision_to_wrap_up": (
                    "Because you did not accept our offer, we can talk again next time."
                ),
                "charges_to_bureau_consent": (
                    "Do you consent to a credit-bureau check for this application? "
                    'Please say "I consent" or "I decline".'
                ),
            },
            {
                edge_id: edge["transfer_message"]
                for edge_id, edge in edges.items()
                if "transfer_message" in edge
            },
        )
        self.assertEqual("none", edges["charges_to_bureau_consent"]["target_response"])
        nodes = {node["id"]: node for node in previous_realtime["handoff"]["nodes"]}
        self.assertEqual(13, len(nodes))
        self.assertEqual(24, len(edges))
        for node_id, node in nodes.items():
            with self.subTest(node=node_id):
                self.assertIsNone(node["config"]["interim_response"])
        rpc = nodes["rpc"]
        self.assertIn(
            "Am I speaking with <calling_first_name>?",
            " ".join(rpc["config"]["instructions"].split()),
        )
        self.assertIn(
            "Could you please tell me your date of birth?",
            " ".join(rpc["config"]["instructions"].split()),
        )
        self.assertIn(
            "Call tools without a spoken lead-in.",
            nodes["offer"]["config"]["instructions"],
        )
        for node_id in ("offer", "appointment"):
            self.assertNotIn(
                "The handoff edge alone says",
                nodes[node_id]["config"]["instructions"],
            )
        for phrase in (
            "I'm checking those details now.",
            "Confirming your identity, just a second.",
            "Checking your offer, one moment.",
            "Saving your appointment info",
        ):
            self.assertNotIn(phrase, json.dumps(previous_realtime))
        end = nodes["end"]
        self.assertEqual(
            {
                "type": "system",
                "name": "end_conversation",
                "description": (
                    "End the active conversation only after its business "
                    "disposition has been recorded. First say one brief, "
                    "context-appropriate closing sentence, then call "
                    "end_conversation as a separate final output item in the "
                    "same response with only a non-empty reason. Produce no "
                    "content after the tool call."
                ),
            },
            end["config"]["tools"][0],
        )
        self.assertEqual("gpt-realtime", realtime["model"])
        for definition in (realtime, cascade):
            self.assertEqual(
                400,
                definition["audio"]["input"]["turn_detection"]["silence_duration_ms"],
            )
        self.assertEqual(
            "whisper-1",
            realtime["audio"]["input"]["transcription"]["model"],
        )
        self.assertIsNone(
            realtime["audio"]["input"]["turn_detection"][
                "end_of_utterance_detection"
            ]
        )
        self.assertEqual(
            "en-IN-Diya:DragonHDLatestNeural",
            realtime["audio"]["output"]["voice"]["name"],
        )
        self.assertEqual("gpt-5.6-luna", cascade["model"])
        self.assertEqual(
            "azure-speech",
            cascade["audio"]["input"]["transcription"]["model"],
        )
        self.assertEqual(
            {
                "model": "smart_end_of_turn_detection",
                "threshold_level": "medium",
                "timeout_ms": 2000,
            },
            cascade["audio"]["input"]["turn_detection"][
                "end_of_utterance_detection"
            ],
        )
        self.assertEqual(
            "en-IN-Diya:DragonHDLatestNeural",
            cascade["audio"]["output"]["voice"]["name"],
        )

    def test_sample_env_defaults_match_committed_model_mode(self) -> None:
        samples = Path(__file__).resolve().parent
        for directory in (
            "example1_finance_with_handoff_realtime",
            "example1_finance_with_handoff_cascade",
            "example2_finance_with_OTP_and_Officer_Search",
            "example3_elevator_service_with_safety_zendesk_and_handoff",
        ):
            sample = samples / directory
            definition = json.loads(
                (sample / "agent.json").read_text(encoding="utf-8")
            )["definition"]
            defaults = {
                key.strip(): value.strip()
                for line in (sample / ".env.example").read_text(
                    encoding="utf-8"
                ).splitlines()
                if line and not line.startswith("#") and "=" in line
                for key, value in [line.split("=", 1)]
            }
            self.assertEqual(definition["model_type"], "managed")
            self.assertNotIn("VOICE_AGENT_MODEL_TYPE", defaults)
            if directory.startswith("example1_finance_with_handoff_"):
                self.assertNotIn("VOICE_AGENT_MODEL", defaults)
            else:
                self.assertEqual(
                    defaults["VOICE_AGENT_MODEL"],
                    definition["model"],
                )

    def test_counts_handoff_and_mcp_call_evidence(self) -> None:
        printer = EventPrinter(verbose=False)
        with contextlib.redirect_stdout(io.StringIO()):
            printer.show(
                {
                    "type": "response.done",
                    "response": {
                        "output": [
                            {
                                "type": "function_call",
                                "name": "handoff",
                            }
                        ]
                    },
                }
            )
            printer.show({"type": "response.mcp_call.completed"})
            printer.show({"type": "mcp_list_tools.completed"})

        summary = printer.summary("agent", "session")
        self.assertEqual(summary["handoff_events"], 1)
        self.assertEqual(summary["mcp_events"], 2)
        self.assertEqual(summary["mcp_call_events"], 1)

if __name__ == "__main__":
    unittest.main()
