from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SnowflakeJobResultResponse(BaseModel):
    job_id: str = Field(..., examples=["8d7f3e18-1e6e-4f20-aeae-4c76f4b7b91e"])
    result: Any = Field(
        ...,
        examples=[
            {
                "pipe_status": {"pendingFileCount": 0},
                "remote_name": "1700000000.json",
                "stage_path": '@"CONHACKS"."CORE"."LANDING_STAGE"/do_sizes',
            }
        ],
    )


class SnowflakeIngestDoSizesExample(SnowflakeJobResultResponse):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "040662b1-7cfb-4631-8337-4e63130e3a9a",
                    "result": {
                        "pipe_status": {
                            "executionState": "RUNNING",
                            "pendingFileCount": 0,
                            "lastIngestedTimestamp": "2026-04-29T22:21:06.262Z",
                            "lastIngestedFilePath": "/1777501264.json/tmp_48e_4_k.json",
                            "pendingHistoryRefreshJobsCount": 0,
                        },
                        "remote_name": "1777501756.json",
                        "stage_path": '@"CONHACKS"."CORE"."LANDING_STAGE"/do_sizes',
                    },
                }
            ]
        }
    }


class SnowflakeTerraformCleanExample(SnowflakeJobResultResponse):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "040662b1-7cfb-4631-8337-4e63130e3a9a",
                    "result": [{"SP_CLEAN_RAW": "ok"}],
                }
            ]
        }
    }


class SnowflakeMetricsCleanExample(SnowflakeJobResultResponse):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "3d7cd15a-99ff-4ab2-b2e0-1b746fcd5b96",
                    "result": [
                        {"status": "Statement executed successfully."},
                        {"SP_CLEAN_RAW": "ok"},
                    ],
                }
            ]
        }
    }


class SnowflakeTerraformUploadResolvedExample(SnowflakeJobResultResponse):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "79bc6137-ccf1-44d9-922b-07a1455f3cb9",
                    "result": {
                        "pipe_status": {
                            "executionState": "RUNNING",
                            "pendingFileCount": 0,
                            "lastIngestedTimestamp": "2026-04-29T19:51:48.386Z",
                            "lastIngestedFilePath": "/resolved_resources.json/tmpvpfnv_sl.json",
                            "pendingHistoryRefreshJobsCount": 0,
                        },
                        "remote_name": "resolved_resources.json",
                        "stage_path": '@"CONHACKS"."CORE"."LANDING_STAGE"/terraform_config',
                    },
                }
            ]
        }
    }


class SnowflakeJobItemsResponse(BaseModel):
    job_id: str = Field(..., examples=["8d7f3e18-1e6e-4f20-aeae-4c76f4b7b91e"])
    items: list[dict[str, Any]]
    limit: int | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "19760e0b-a8c0-40bc-9e36-65b7b2794f34",
                    "items": [
                        {
                            "CREATED_AT": "2026-04-29T12:52:52.895000",
                            "RESOURCE_ID": "222651441",
                            "OLD_SIZE": "s-4vcpu-8gb",
                            "NEW_SIZE": "s-1vcpu-1gb",
                            "ESTIMATED_SAVINGS": "42.00",
                            "REASON": "cpu_mem_sizes_catalog",
                        }
                    ],
                    "limit": 50,
                }
            ]
        }
    }


class SnowflakePipeStatusResponse(BaseModel):
    job_id: str
    pipe: str
    pipe_fqn: str
    raw_table: str
    pipe_status: Any | None = None
    copy_history: list[dict[str, Any]]


class SnowflakeCortexChatResponse(BaseModel):
    job_id: str
    answer: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "0516f930-a2f6-4c17-9c2a-00a6d7a1a618",
                    "answer": "Based on the provided data, here's an overview of your current usage:\\n\\n**Resource Usage:**\\n\\n* You have one DigitalOcean Droplet (resource ID: 222651441) with the following characteristics:\\n\\t+ Name: app\\n\\t+ Region: nyc3\\n\\t+ Size: s-4vcpu-8gb (currently)\\n\\t+ Image: ubuntu-22-04-x64\\n\\t+ Tags: conhacks, dev\\n\\n**CPU Usage:**\\n\\n* The average CPU usage over the last 5 samples is:\\n\\t+ User: 1.84% (range: 1.65% - 2.05%)\\n\\t+ System: 0.75% (range: 0.70% - 0.80%)\\n\\t+ Idle: 97.13% (range: 96.85% - 97.30%)\\n\\t+ Iowait: 0.11% (range: 0.08% - 0.15%)\\n\\t+ Steal: 0.05% (range: 0.03% - 0.06%)\\n\\n**Cost Optimization Recommendation:**\\n\\n* Based on the current usage, our analysis suggests that you can downsize your Droplet to s-1vcpu-1gb, which could result in estimated savings of 42%.\\n\\nPlease note that this recommendation is based on a limited set of data and might not reflect your actual usage patterns. It's essential to monitor your resources and adjust the size accordingly to ensure optimal performance and cost efficiency.",
                }
            ]
        }
    }


class SnowflakeCortexSummarizeResponse(BaseModel):
    job_id: str
    status: str
    inserted: int
    summaries: list[dict[str, Any]]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "d99b3eb2-deb2-4559-b8fd-7d30b0e2b36f",
                    "status": "ok",
                    "inserted": 0,
                    "summaries": [
                        {
                            "CREATED_AT": "2026-04-29T13:57:23.912000",
                            "SUGGESTION_TYPE": "recommendation_summary",
                            "RESOURCE_ID": "222651441",
                            "EXPLANATION": "Let me break down the recommendation for you in simple terms.\\n\\n**What's happening?**\\nWe've analyzed the usage of a specific resource (with ID 222651441) and found an opportunity to save some money.\\n\\n**The issue:**\\nThe resource is currently using a size that's too big for its needs. It's like renting a big house when you only need a small apartment. The current size is \\\"s-4vcpu-8gb\\\", which means it has 4 virtual CPUs and 8 GB of memory.\\n\\n**The recommendation:**\\nWe suggest downsizing to a smaller size, \\\"s-1vcpu-1gb\\\", which has 1 virtual CPU and 1 GB of memory. This size is more suitable for the resource's actual usage.\\n\\n**Why is this a good idea?**\\nThe metrics payload JSON shows that the resource has been idle most of the time, with CPU usage ranging from 96.85% to 97.30% (which is actually very low). This means the resource is not utilizing its full capacity, and a smaller size would be sufficient.\\n\\n**The benefit:**\\nBy downsizing, you can save an estimated $42.00 per month. That's a nice chunk of change!\\n\\nIn summary, we recommend reducing the size of the resource to match its actual usage, which will result in significant cost savings.",
                        }
                    ],
                }
            ]
        }
    }


class SnowflakeSetupResponse(BaseModel):
    job_id: str
    status: str
    note: str


class SnowflakeWorkflowsSetupResponse(BaseModel):
    job_id: str
    status: str
    note: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "042f2e06-8808-463c-8fe0-6d52f752f1c2",
                    "status": "ok",
                    "note": "Workflows created/verified (cleaning/analyze/cortex procedures and tasks).",
                }
            ]
        }
    }


class SnowflakeJobsGetResponse(BaseModel):
    job: dict[str, Any]
