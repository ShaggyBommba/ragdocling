# Test Summary

## Overview

| Layer | Files | Tests |
|---|---|---|
| Unit — Domain | 7 | 95 |
| Unit — Application (Use Cases / Handlers) | 3 | 33 |
| Unit — Infrastructure (Repositories) | 5 | 23 |
| Unit — Infrastructure (Transformers) | 6 | 37 |
| Unit — Infrastructure (Bus / Embedder / Reranker / DTO) | 4 | 34 |
| Integration | 3 | 17 |
| **Total** | **28** | **239** |

---

## Unit Tests — Domain

### `test_workspace.py` (16 tests)
| Test | What it checks |
|---|---|
| `test_create_workspace_from_name` | Created workspace has correct name and empty state |
| `test_deterministic_workspace_id_from_name` | Same name always produces the same ID |
| `test_different_workspace_names_produce_different_ids` | Different names produce different IDs |
| `test_workspace_created_at_before_updated_at` | `created_at <= updated_at` timestamp invariant |
| `test_add_collection_to_workspace` | Adding a collection increments count and is retrievable |
| `test_add_multiple_collections` | Multiple collections can coexist |
| `test_add_duplicate_collection_identity_raises_error` | Duplicate collection ID raises `DomainError` |
| `test_remove_collection_from_workspace` | Removal decrements count |
| `test_remove_nonexistent_collection_raises_error` | Removing non-existent collection raises error |
| `test_workspace_empty_after_removing_all_collections` | State is clean after all removals |
| `test_add_collection_updates_workspace_timestamp` | `updated_at` advances on collection add |
| `test_remove_collection_updates_workspace_timestamp` | `updated_at` advances on collection remove |
| `test_find_collection_by_identity` | Lookup by ID returns correct collection |
| `test_find_collection_by_identity_returns_none` | Non-existent ID returns `None` |
| `test_workspace_with_multiple_collections` | Workspace handles 3 collections correctly |
| `test_workspace_invariants_collection_uniqueness` | Duplicate collection IDs are rejected |

### `test_collection.py` (24 tests)
| Test | What it checks |
|---|---|
| `test_create_collection` | Name set, zero artifacts on creation |
| `test_create_collection_with_deterministic_id` | Same name → same ID |
| `test_create_collection_different_names_different_ids` | Different names → different IDs |
| `test_create_collection_different_workspaces_different_ids` | Workspace ID is part of ID derivation |
| `test_add_artifact_to_collection` | Artifact addition increments count |
| `test_add_multiple_artifacts` | Multiple artifacts coexist |
| `test_add_duplicate_artifact_raises_error` | Duplicate artifact ID raises error |
| `test_remove_artifact_from_collection` | Removal decrements count |
| `test_remove_nonexistent_artifact_raises_error` | Removing non-existent artifact raises error |
| `test_find_artifact_by_identity` | Lookup by ID returns correct artifact |
| `test_find_artifact_by_identity_returns_none` | Non-existent ID returns `None` |
| `test_add_artifact_exceeding_count_limit_raises_error` | Exceeding 100-file cap raises error |
| `test_add_artifact_exceeding_size_limit_raises_error` | Exceeding 10 MB size cap raises error |
| `test_default_max_count_files` | Default max is 100 files |
| `test_default_max_file_size_kb` | Default max is 10240 KB |
| `test_update_collection_name` | Name can be updated |
| `test_update_collection_name_updates_timestamp` | `updated_at` advances on rename |
| `test_add_artifact_updates_timestamp` | `updated_at` advances on artifact add |
| `test_remove_artifact_updates_timestamp` | `updated_at` advances on artifact remove |
| `test_created_at_before_updated_at` | Timestamp invariant holds |

### `test_artifact.py` (17 tests)
| Test | What it checks |
|---|---|
| `test_create_artifact` | Artifact created without content |
| `test_create_artifact_with_content` | `has_content` flag set when content provided |
| `test_artifact_identity_from_address` | ID derived from checksum + collection ID |
| `test_set_content_from_bytes` | Content set from `bytes` |
| `test_set_content_from_bytesio` | Content set from `BytesIO` |
| `test_set_content_from_bytesio_with_position` | Reads from start regardless of stream position |
| `test_set_content_updates_timestamp` | `updated_at` advances on content set |
| `test_set_content_updates_metadata_size` | Metadata size reflects actual content length |
| `test_content_property_raises_when_not_loaded` | Accessing unloaded content raises error |
| `test_has_content_property` | `has_content` reflects load state |
| `test_as_blob_converts_to_blob` | Artifact converts to `Blob` object |
| `test_as_blob_raises_when_content_not_loaded` | Blob conversion without content raises error |
| `test_size_kb_property` | `size_kb` calculated correctly for 1 KB |
| `test_size_mb_property` | `size_mb` calculated correctly for 1 MB |
| `test_size_kb_fractional` | Fractional KB sizes handled |
| `test_artifact_created_at_before_updated_at` | Timestamp invariant holds |
| `test_artifact_address_matches_metadata_filename` | Address filename matches metadata |

### `test_ids.py` (15 tests)
| Test | What it checks |
|---|---|
| `WorkspaceID.test_generate_creates_random_id` | Random ID generation |
| `WorkspaceID.test_from_name_creates_deterministic_id` | Same name → same UUID |
| `WorkspaceID.test_from_name_case_insensitive` | Name lookup is case-insensitive |
| `WorkspaceID.test_from_hex_parses_valid_uuid` | Valid hex string parsed |
| `WorkspaceID.test_from_hex_raises_on_invalid_uuid` | Invalid hex raises `ValueError` |
| `WorkspaceID.test_str_returns_hex_without_hyphens` | `str()` returns 32-char hex |
| `WorkspaceID.test_repr_returns_uuid` | `repr()` returns UUID string |
| `CollectionID.test_generate_creates_random_id` | Random ID generation |
| `CollectionID.test_from_name_requires_workspace_id` | Workspace ID is required |
| `CollectionID.test_from_name_different_workspace_ids_produce_different_ids` | Workspace scope enforced |
| `CollectionID.test_from_hex_parses_valid_uuid` | Valid hex string parsed |
| `CollectionID.test_str_returns_hex_without_hyphens` | `str()` format |
| `ArtifactID.test_generate_creates_random_id` | Random ID generation |
| `ArtifactID.test_from_address_creates_deterministic_id` | ID derived from checksum |
| `ArtifactID.test_from_address_case_insensitive` | Checksum comparison is case-insensitive |

### `test_metadata.py` (9 tests)
| Test | What it checks |
|---|---|
| `test_create_artifact_metadata` | All fields stored correctly |
| `test_create_with_default_author` | Default author is `"unknown"` |
| `test_size_kb_property` | `size_kb` calculation |
| `test_size_mb_property` | `size_mb` calculation |
| `test_size_kb_fractional` | Fractional KB sizes |
| `test_size_mb_fractional` | Fractional MB sizes |
| `test_str_representation` | `str()` includes filename, size, MIME type |
| `test_repr_representation` | `repr()` includes filename, source, MIME type |
| `test_metadata_is_hashable` | Usable as dict key / set member |

### `test_storage.py` (23 tests)
| Test | What it checks |
|---|---|
| `StoragePath.test_create_storage_path` | Bucket and prefix stored |
| `StoragePath.test_create_storage_path_empty_prefix` | Empty prefix supported |
| `StoragePath.test_at_appends_to_prefix` | Multiple parts joined correctly |
| `StoragePath.test_at_with_empty_prefix` | Appending to empty prefix |
| `StoragePath.test_at_single_part` | Single part appended |
| `StoragePath.test_parent_goes_up_one_level` | Last path component removed |
| `StoragePath.test_parent_at_root_returns_self` | Parent of root returns empty prefix |
| `StoragePath.test_parent_single_level` | Parent of single level returns empty |
| `StoragePath.test_resolve_creates_object_address` | `ObjectAddress` created from path |
| `ObjectAddress.test_create_object_address` | All fields stored |
| `ObjectAddress.test_create_object_address_with_version` | `version_id` optional field |
| `ObjectAddress.test_key_combines_prefix_and_filename` | `key` = prefix + filename |
| `ObjectAddress.test_key_without_prefix` | Key is just filename when no prefix |
| `ObjectAddress.test_from_uri_parses_s3_uri` | S3 URI parsed correctly |
| `ObjectAddress.test_from_uri_without_prefix` | URI without prefix parsed |
| `ObjectAddress.test_from_uri_deep_nesting` | Deep nested path parsed |
| `ObjectAddress.test_from_uri_raises_on_invalid_uri` | Invalid URI raises `ValueError` |
| `ObjectAddress.test_from_uri_raises_on_non_s3_scheme` | Non-S3 scheme raises error |
| `ObjectAddress.test_s3_uri_property` | S3 URI generated correctly |
| `ObjectAddress.test_s3_uri_without_prefix` | URI without prefix |
| `ObjectAddress.test_s3_uri_with_version_id` | `?versionId=` appended |
| `ObjectAddress.test_str_returns_s3_uri` | `str()` returns S3 URI |
| `Blob.test_create_blob` | Address, content, media type stored |
| `Blob.test_create_blob_default_media_type` | Default is `application/octet-stream` |
| `Blob.test_size_bytes_property` | Size calculated correctly |
| `Blob.test_size_bytes_empty_content` | Zero size for empty content |
| `Blob.test_size_bytes_large_content` | Large content sized correctly |
| `Blob.test_blob_is_hashable` | Usable as dict key / set member |

---

## Unit Tests — Infrastructure: Repositories

All repository tests use SQLite in-memory (via `aiosqlite`) — no running Postgres required.

### `test_workspace_repository.py` (6 tests)
| Test | What it checks |
|---|---|
| `test_roundtrip_conversion` | `WorkspaceAcl` domain → ORM → domain round-trip |
| `test_save_workspace` | Workspace persisted without error |
| `test_get_workspace_by_name` | Retrieved workspace matches saved name |
| `test_get_all_workspaces` | All saved workspaces returned |
| `test_delete_workspace` | Deleted workspace returns `None` on lookup |
| `test_workspace_not_found` | Non-existent workspace returns `None` |

### `test_collection_repository.py` (6 tests)
| Test | What it checks |
|---|---|
| `test_roundtrip_conversion` | `CollectionAcl` round-trip |
| `test_save_collection` | Collection persisted |
| `test_get_collection_by_id` | Retrieved collection name correct |
| `test_get_collections_by_workspace` | Workspace-scoped listing returns ≥1 |
| `test_delete_collection` | Deleted collection returns `None` |
| `test_collection_not_found` | Non-existent collection returns `None` |

### `test_pipeline_repository.py` (6 tests)
| Test | What it checks |
|---|---|
| `test_roundtrip_conversion` | `PipelineAcl` round-trip |
| `test_save_pipeline` | Pipeline persisted |
| `test_get_pipeline_by_id` | Retrieved pipeline ID matches |
| `test_get_pipelines_by_collection` | Collection-scoped listing returns ≥1 |
| `test_delete_pipeline` | Deleted pipeline returns `None` |
| `test_pipeline_not_found` | Non-existent pipeline returns `None` |

### `test_metadata_repository.py` (6 tests)
| Test | What it checks |
|---|---|
| `test_roundtrip_conversion` | `ArtifactMetadataAcl` round-trip |
| `test_save_artifact` | Artifact metadata persisted |
| `test_get_artifact_by_id` | Retrieved artifact filename correct |
| `test_get_artifacts_by_collection_id` | Collection-scoped listing returns ≥1 |
| `test_delete_artifact` | Deleted artifact returns `None` |
| `test_artifact_not_found` | Non-existent artifact returns `None` |

### `test_blob_repository.py` (8 tests)
| Test | What it checks |
|---|---|
| `test_from_domain` | `BlobArtifactAcl.from_domain` produces correct dict |
| `test_to_domain` | `BlobArtifactAcl.to_domain` reconstructs `Blob` |
| `test_roundtrip_conversion` | Bidirectional ACL conversion |
| `test_save_blob` | Blob saved and retrievable |
| `test_get_artifact_by_address` | Retrieval by `ObjectAddress` |
| `test_delete_artifact` | Deleted blob returns `None` |
| `test_list_artifacts_in_bucket` | Prefix-scoped listing |
| `test_artifact_not_found` | Missing address returns `None` |

---

## Unit Tests — Infrastructure: Transformers

All transformer tests mock `httpx.AsyncClient.post` — no LLM endpoint required.

### `test_pattern_match.py` (7 tests)
| Test | What it checks |
|---|---|
| `test_matching_pattern_sets_tags` | Matching regex adds pattern name to `tags` |
| `test_no_match_sets_none` | No match leaves `tags` as `None` |
| `test_multiple_patterns_all_matching` | All matching pattern names collected |
| `test_partial_match` | Only matching patterns collected |
| `test_multiple_chunks_independent` | Each chunk tagged independently |
| `test_empty_document_returns_document` | No-op on empty document |
| `test_returns_same_document` | Document object identity preserved |

### `test_url_extract.py` (7 tests)
| Test | What it checks |
|---|---|
| `test_extracts_single_url` | Single URL extracted into `urls` |
| `test_extracts_multiple_urls` | Multiple URLs all captured |
| `test_deduplicates_urls` | Duplicate URLs removed |
| `test_no_urls_sets_none` | No URLs → `urls` is `None` |
| `test_preserves_url_order` | Extraction order maintained |
| `test_multiple_chunks_processed` | Each chunk processed independently |
| `test_http_and_https_both_extracted` | Both schemes extracted |

### `test_query_generation.py` (5 tests)
| Test | What it checks |
|---|---|
| `test_sets_positive_and_negative_queries` | LLM JSON parsed into `positive_queries` and `negative_queries` |
| `test_llm_failure_sets_none` | Both fields `None` on exception |
| `test_invalid_json_sets_none` | Both fields `None` on JSON parse error |
| `test_multiple_chunks_called_concurrently` | One LLM call per chunk, all assigned |
| `test_empty_lists_set_none` | Empty lists coerced to `None` |

### `test_text_enhancer.py` (5 tests)
| Test | What it checks |
|---|---|
| `test_replaces_content_with_enhanced_text` | LLM response replaces `chunk.content` |
| `test_llm_failure_preserves_original` | Original content kept on exception |
| `test_empty_llm_response_preserves_original` | Whitespace-only response falls back to original |
| `test_multiple_chunks_each_enhanced` | Each chunk enhanced independently |
| `test_returns_same_document` | Document object identity preserved |

### `test_contextual_summary.py` (5 tests)
| Test | What it checks |
|---|---|
| `test_prepends_summary_to_content` | Content becomes `"{summary}\n\n{original}"` |
| `test_llm_failure_preserves_original` | Original content kept on exception |
| `test_empty_summary_preserves_original` | Empty summary falls back to original |
| `test_multiple_chunks_each_get_summary` | Each chunk summarized independently |
| `test_summary_is_stripped` | Leading/trailing whitespace removed from summary |

### `test_entity_extractor.py` (8 tests)
| Test | What it checks |
|---|---|
| `test_adds_entities_to_tags` | Extracted entities written to `tags` |
| `test_merges_with_existing_tags` | New entities merged with existing tags |
| `test_deduplicates_with_existing_tags` | No duplicate tags after merge |
| `test_llm_failure_leaves_tags_unchanged` | Tags unchanged on exception |
| `test_invalid_json_leaves_tags_unchanged` | Tags unchanged on JSON parse error |
| `test_empty_entities_skips_chunk` | Empty entity list → tags remain `None` |
| `test_multiple_chunks_processed` | Each chunk processed independently |
| `test_returns_same_document` | Document object identity preserved |

---

---

## Unit Tests — Application Layer

### `test_retrieve_usecase.py` (15 tests)
| Test | What it checks |
|---|---|
| `test_returns_empty_when_pipeline_not_found` | Non-existent pipeline → empty list |
| `test_embeds_query_and_calls_search` | Embedder and search both called for valid pipeline |
| `test_returns_empty_when_no_search_results` | Empty search results → empty list |
| `test_search_called_with_correct_top_k` | `top_k` from DTO passed to `search` |
| `test_search_called_with_oversample_when_reranker_enabled` | Oversamples with reranker `oversample` value |
| `test_reranker_called_when_enabled_and_results_exist` | Reranker invoked when enabled and results present |
| `test_reranker_not_called_when_disabled` | Reranker skipped when `enabled=False` |
| `test_search_passes_tags_filter` | `tags` forwarded to `search` |
| `test_search_passes_origins_filter` | `origins` forwarded to `search` |
| `test_result_dto_fields_populated` | DTO `origin` and `score` match point data |
| `test_expand_links_fetches_referenced_origins` | `fetch_by_origin` called with chunk's `references` |
| `test_expand_links_deduplicates_already_present_points` | Points already in results not re-added |
| `test_expand_links_skipped_when_no_references` | `fetch_by_origin` not called when no references |
| `test_expand_links_disabled_does_not_call_fetch` | `fetch_by_origin` skipped when `expand_links=False` |
| `test_expand_links_appends_with_score_zero` | Expanded points get `score=0.0` |

### `test_convert_handler.py` (11 tests)
| Test | What it checks |
|---|---|
| `test_returns_embeddings_on_success` | Happy path returns embeddings list |
| `test_returns_empty_when_artifact_not_found` | Missing artifact → empty list |
| `test_returns_empty_when_presigned_url_not_found` | Missing presigned URL → empty list |
| `test_returns_empty_when_no_pipelines` | No pipelines → empty list |
| `test_returns_empty_when_no_production_pipeline` | No PRODUCTION pipeline → empty list |
| `test_extractor_called_with_presigned_url` | Extractor receives correct URL |
| `test_delete_by_origin_called_before_save` | Delete happens before save (overwrite order) |
| `test_embeddings_saved_to_repo` | `save_many` called after embedding |
| `test_returns_empty_when_no_chunks_extracted` | No chunks → no embeddings, returns `[]` |
| `test_transformer_applied_when_registered` | Registered transformer's `transform` called |
| `test_unknown_transformer_skipped_gracefully` | Unknown transformer name doesn't raise |

### `test_cleanup_handler.py` (7 tests)
| Test | What it checks |
|---|---|
| `test_returns_empty_when_artifact_not_found` | Missing artifact → early return `[]` |
| `test_deletes_embeddings_for_each_pipeline` | One `delete_by_origin` call per pipeline |
| `test_deletes_blob_from_storage` | `delete_blob` called once |
| `test_deletes_artifact_metadata` | `delete_artifact` called once |
| `test_skips_embedding_deletion_when_no_pipelines` | No pipelines → no Qdrant deletes |
| `test_returns_status_dict_on_success` | Returns `{"status": "cleaned", ...}` |
| `test_delete_by_origin_called_with_artifact_source` | Origin passed to `delete_by_origin` matches artifact source |

---

## Unit Tests — Infrastructure (Bus / Embedder / Reranker / DTO)

### `test_event_bus.py` (6 tests)
| Test | What it checks |
|---|---|
| `test_register_and_publish_sync_handler` | Sync handler receives event |
| `test_register_and_publish_async_handler` | Async handler receives event |
| `test_multiple_handlers_all_called` | All registered handlers for an event type called |
| `test_no_handler_registered_does_not_raise` | Publishing without handlers is safe |
| `test_handler_not_called_for_different_event_type` | Handler not called for unrelated event |
| `test_handler_exception_propagates` | Exceptions in handlers bubble up |

### `test_embedder.py` (5 tests)
| Test | What it checks |
|---|---|
| `test_embed_returns_embedding_with_vector` | `embed()` returns `Embedding` with correct vector |
| `test_embed_many_returns_one_embedding_per_chunk` | One embedding per input chunk |
| `test_embed_calls_correct_url` | POST goes to `.../embeddings` endpoint |
| `test_embed_passes_model_in_request` | `model` from settings included in request body |
| `test_embed_single_chunk_produces_one_result` | Single-chunk `embed_many` returns 1 result |

### `test_reranker.py` (5 tests)
| Test | What it checks |
|---|---|
| `test_rerank_returns_ranked_results` | `rerank()` returns `RankedResult` list |
| `test_rerank_results_sorted_by_score_descending` | Results ordered highest score first |
| `test_rerank_top_n_limits_results` | `top_n` limits result count |
| `test_rerank_preserves_original_index` | `RankedResult.index` matches original document position |
| `test_rerank_empty_documents_returns_empty` | Empty input → empty output |

### `test_retrieve_dto.py` (17 tests)
| Test | What it checks |
|---|---|
| `_build_formatted_text.test_includes_result_header` | Header line contains `# Result N/M` |
| `_build_formatted_text.test_includes_score_in_header` | Score appears in header |
| `_build_formatted_text.test_includes_origin_in_frontmatter` | Origin in YAML frontmatter |
| `_build_formatted_text.test_includes_title_as_h2` | Title rendered as `## Title` |
| `_build_formatted_text.test_no_title_omits_h2` | No title → no h2 |
| `_build_formatted_text.test_includes_pages_in_frontmatter` | Pages in frontmatter |
| `_build_formatted_text.test_includes_tags_in_frontmatter` | Tags listed in frontmatter |
| `_build_formatted_text.test_includes_attachments_section` | Attachments rendered under `## Attachments` |
| `RetrieveResultDTO.test_from_point_populates_score` | `score` from point |
| `RetrieveResultDTO.test_from_point_score_override` | `score_override` takes precedence |
| `RetrieveResultDTO.test_from_point_populates_origin` | `origin` from payload |
| `RetrieveResultDTO.test_from_point_populates_title` | `title` from payload |
| `RetrieveResultDTO.test_from_point_none_title` | `None` title preserved |
| `RetrieveResultDTO.test_from_point_populates_pages` | `pages` from payload |
| `RetrieveResultDTO.test_from_point_text_contains_content` | Formatted text includes raw content |
| `RetrieveResultDTO.test_from_point_index_and_total_in_text` | Index/total in formatted text |
| `RetrieveResultDTO.test_from_point_empty_payload` | Empty payload → defaults without crash |

---

## Unit Tests — Domain: Pipeline Aggregate

### `test_pipeline.py` (21 tests)
| Test | What it checks |
|---|---|
| `test_create_pipeline_has_correct_collection` | `collection_id` stored |
| `test_create_pipeline_default_lifecycle_is_staging` | Default lifecycle is `STAGING` |
| `test_create_pipeline_with_explicit_production_lifecycle` | Explicit lifecycle respected |
| `test_create_pipeline_has_default_transformations` | Default transformers list non-empty |
| `test_create_pipeline_deterministic_id_for_same_settings` | Same settings → same ID |
| `test_create_pipeline_different_collections_produce_different_ids` | Different collections → different IDs |
| `test_create_pipeline_has_identity` | Identity is not `None` |
| `test_created_at_before_updated_at` | Timestamp invariant |
| `test_deploy_sets_production` | `deploy()` → `PRODUCTION` |
| `test_stage_sets_staging` | `stage()` → `STAGING` |
| `test_archive_sets_archived` | `archive()` → `ARCHIVED` |
| `test_deploy_updates_timestamp` | `updated_at` advances on deploy |
| `test_stage_updates_timestamp` | `updated_at` advances on stage |
| `test_archive_updates_timestamp` | `updated_at` advances on archive |
| `test_cannot_deploy_archived_pipeline` | Archived pipeline stays archived on deploy |
| `test_cannot_stage_archived_pipeline` | Archived pipeline stays archived on stage |
| `test_cannot_archive_already_archived_pipeline` | No crash on double archive |
| `test_default_transformations_include_pattern_match` | `PatternMatchTransformer` in defaults |
| `test_default_transformations_include_url_extract` | `UrlExtractTransformer` in defaults |
| `test_default_transformations_include_query_generation` | `QueryGenerationTransformer` in defaults |
| `test_custom_transformations_override_defaults` | Provided transformers replace defaults |

---

## Integration Tests

These require live Postgres, Redis, Qdrant, and MinIO (via `make docker-up`).

### `test_workspace_endpoints.py` (5 tests)
| Test | What it checks |
|---|---|
| `test_create_workspace_endpoint` | `POST /api/v1/workspaces` → 200, correct payload |
| `test_list_workspaces_endpoint` | `GET /api/v1/workspaces` → 200, list |
| `test_get_workspace_endpoint` | `GET /api/v1/workspaces/{id}` → 200, correct workspace |
| `test_update_workspace_endpoint` | `PUT /api/v1/workspaces/{id}` → 200, name updated |
| `test_delete_workspace_endpoint` | `DELETE /api/v1/workspaces/{id}` → 204 |

### `test_collection_endpoints.py` (5 tests)
| Test | What it checks |
|---|---|
| `test_create_collection_endpoint` | `POST /api/v1/workspaces/{wid}/collections` → 200, correct payload |
| `test_list_collections_endpoint` | `GET /api/v1/workspaces/{wid}/collections` → 200, list |
| `test_get_collection_endpoint` | `GET /api/v1/workspaces/{wid}/collections/{id}` → 200 |
| `test_update_collection_endpoint` | `PUT /api/v1/workspaces/{wid}/collections/{id}` → 200, name updated |
| `test_delete_collection_endpoint` | `DELETE /api/v1/workspaces/{wid}/collections/{id}` → 204 |

### `test_pipeline_endpoints.py` (7 tests)
| Test | What it checks |
|---|---|
| `test_list_collection_pipelines_endpoint` | `GET .../pipelines` → 200, ≥1 pipeline |
| `test_get_collection_pipeline_endpoint` | `GET .../pipelines/{id}` → 200, correct ID |
| `test_promote_pipeline_endpoint` | `POST .../pipelines/{id}/promote` → 200 |
| `test_demote_pipeline_endpoint` | `POST .../pipelines/{id}/demote` → 200 |
| `test_get_production_pipeline_endpoint` | `GET .../pipelines/production` → 200 |
| `test_get_staging_pipeline_endpoint_not_found` | `GET .../pipelines/staging` → 404 (none promoted yet) |
| `test_get_archived_pipeline_endpoint_not_found` | `GET .../pipelines/archived` → 404 (none archived yet) |

---

## What Is NOT Tested

### Application layer (use cases)
- `UploadFileUseCase` — file upload flow, Celery task dispatch
- `PromotePipelineUseCase` / `DemotePipelineUseCase` — lifecycle use cases (lifecycle logic covered in `test_pipeline.py`; endpoint covered via integration)

### Infrastructure
- `QdrantEmbeddingRepository` — `search`, `save_many`, `fetch_by_origin`, `delete_by_origin` (requires live Qdrant)
- `DoclingExtractor` / `MLXExtractor` — document parsing and OCR (requires ML models)
- `Celery` task execution — async worker retry/backoff behavior (requires broker)

### Transformer edge cases
- Transformer registry auto-discovery of new transformer classes
- Concurrency under high semaphore contention
- Partial LLM streaming responses
- Transformer ordering effects (e.g. summary after enhancement vs. before)

### API
- `POST /api/v1/workspaces/{wid}/collections/{cid}/artifacts` — full artifact upload with file content
- `DELETE /api/v1/workspaces/{wid}/collections/{cid}/artifacts/{id}` — artifact deletion and Qdrant cleanup
- `POST .../pipelines/{id}/retrieve` — retrieval endpoint with filters and link expansion
- Auth / authorization — no authentication layer tested
- Error responses — 400/422/500 response bodies not asserted
- Pagination — list endpoints only assert `len >= 1`, not cursor/page behaviour
