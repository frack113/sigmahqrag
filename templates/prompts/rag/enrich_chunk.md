You are enhancing a Sigma specification document section for vector search retrieval.
Given the following document section, provide:
1. A concise summary in 2-3 sentences (max 150 words)
2. A comma-separated list of 8-20 key search keywords/phrases

Rules:
- Summary must capture: the Sigma attribute/section being defined, its purpose, valid values or syntax rules, and any YAML examples shown
- Keywords MUST include ALL of these categories present in the section:
  * Exact YAML attribute names (e.g. `title`, `logsource`, `detection`, `condition`, `related`, `type`, `group-by`, `timespan`)
  * Exact modifier names if mentioned (e.g. `contains`, `startswith`, `endswith`, `all`, `re`, `base64`, `cidr`, `exists`, `cased`, `neq`, `expand`, `fieldref`, `windash`, `utf16le`)
  * Valid attribute values exactly as written (e.g. `stable`, `test`, `experimental`, `deprecated`, `unsupported`; `informational`, `low`, `medium`, `high`, `critical`; `event_count`, `value_count`, `temporal`, `temporal_ordered`, `value_sum`, `value_avg`, `value_percentile`)
  * Condition operators (e.g. `gt`, `gte`, `lt`, `lte`, `eq`, `neq`)
  * Time span format patterns (e.g. `5m`, `1h`, `30s`, `2d`, `number + letter`)
  * Tag namespace patterns (e.g. `attack.t1059`, `cve.2021-44228`, `tlp.red`, `car.2016-04-005`, `stp.4`)
  * Field name conventions if discussed (e.g. `CommandLine`, `Image`, `ProcessId`, `User`, `EventID`, `ParentImage`)
  * YAML syntax rules (single quotes, UTF-8, LF line breaks, 4-space indentation)
  * File naming conventions (prefixes like `mf_` for filters, `mr_` for correlation; 10-70 chars, lowercase, `_`, `.yml`)
  * Detection block concepts: search-identifier, selection, filter, map evaluation (AND), list evaluation (OR)
  * Wildcard patterns (`?`, `*`, `\*`, `\?`) and escape characters
  * Placeholder syntax (`%Servers%`, `%name%`) and the `expand` modifier
  * Condition expression operators: `and`, `or`, `not`, `all of them`, `1 of selection*`, brackets for grouping
- Include Q&A patterns if the section contains questions (e.g. "what is title field", "how to mark rule stable")
- Include both exact Sigma syntax terms AND conversational phrases users would actually type (e.g. both `"group-by"` and `"how to group events"`)
- Focus on domain-specific concepts (Sigma/Sigma rule terminology), not generic words like "document", "section", "field"
- Use English even if the source text is in another language
- Output format (EXACTLY):

Summary:
[your 2-3 sentence summary here]

Keywords:
[comma-separated keywords here]

Document section:
---
{text}
---

Summary:
