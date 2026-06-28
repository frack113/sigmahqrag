# Sigma Specification Q/A

## Rules Specification (sigma-rules-specification.md)

### File Structure - YAML

**Q:** What file format does Sigma use for rules?
**A:** Sigma rules are written in YAML format (yaml.org/spec/1.2.2/), using UTF-8 encoding, LF line breaks, and 4-space indentation.

**Q:** How should string values be written in a Sigma rule file?
**A:** String values should use single quotes `'`. If the string contains a single quote, double quotes may be used instead. Numeric values use no quotes.

**Q:** What are the filename conventions for Sigma rules?
**A:** Filenames should be 10-70 characters, all lowercase, using `_` instead of spaces, and the `.yml` extension.

### Schema

**Q:** Where is the formal schema defined for Sigma detection rules?
**A:** The JSON schema is defined in `sigma-detection-rule-schema.json` in the `json-schema` directory.

### Title

**Q:** What is the `title` field used for in a Sigma rule?
**A:** The `title` provides a brief description of what the rule detects, with a maximum of 256 characters.

**Q:** Which field is mandatory for a brief description of what the rule detects?
**A:** The `title` field. It is the only mandatory top-level field alongside `logsource` and `detection`.

### Identification (id / related)

**Q:** What is the `id` attribute used for?
**A:** The `id` is a globally unique identifier (UUID v4) for the rule, used for tracking, referencing, and relationship management.

**Q:** How can you express relationships between Sigma rules?
**A:** Use the `related` attribute with one or more entries containing an `id` and a `type` (derived, obsolete, merged, renamed, similar).

**Q:** What does the `related` type `derived` mean?
**A:** It means the rule was derived from the referred rule(s), which may remain active.

**Q:** How do you mark that a rule replaces another one?
**A:** Use `related` with type `obsolete`.

### Name

**Q:** What is the `name` attribute for?
**A:** The `name` is a unique human-readable identifier used instead of the `id` in correlation rules to improve readability.

**Q:** How can you improve readability of a correlation rule referencing detection rules?
**A:** By using the `name` attribute in the referenced rules, which can then be used as a reference in the correlation rule's `rules` field.

### Taxonomy

**Q:** What does the `taxonomy` field define in a Sigma rule?
**A:** It defines field names, field values, and logsource names used in the rule (e.g., `process_command_line` vs `CommandLine`).

**Q:** How can you use custom field names that differ from the default Sigma taxonomy?
**A:** Set the `taxonomy` attribute to a non-default taxonomy (e.g., `ocsf`). The tool must handle the transformation into the default taxonomy.

**Q:** What is the default taxonomy in Sigma?
**A:** The default taxonomy is `sigma`.

### Status

**Q:** What status values are available in Sigma?
**A:** `stable`, `test`, `experimental`, `deprecated`, and `unsupported`.

**Q:** How do you mark a rule as ready for production use?
**A:** Set its `status` to `stable`.

**Q:** Which status indicates a rule cannot be used in its current state?
**A:** `unsupported`.

### Description

**Q:** What is the `description` field for?
**A:** It provides a short and accurate description of the malicious or suspicious activity the rule detects (max 65,535 characters).

**Q:** Which field should you use to explain the context of a rule?
**A:** The `description` field. It is optional.

### License

**Q:** How do you declare the license of a Sigma rule?
**A:** Use the `license` attribute with a value following the SPDX ID specification.

**Q:** What format should the `license` field follow?
**A:** The SPDX ID specification (https://spdx.org/ids).

### Author

**Q:** How do you credit the creator of a rule?
**A:** Use the `author` attribute. Multiple authors are separated by commas.

**Q:** How do you specify multiple authors?
**A:** Separate them by a comma in the `author` field (e.g., `author: Florian Roth, Thomas Patzke`).

### References

**Q:** How do you reference sources a rule was derived from?
**A:** Use the `references` attribute with a list of URLs or citations.

**Q:** Which field provides background sources for a rule?
**A:** The `references` field (optional).

### Date

**Q:** How do you record the creation date of a rule?
**A:** Use the `date` attribute in ISO 8601 format (YYYY-MM-DD).

### Modified

**Q:** What is the `modified` field used for?
**A:** It records the last modification date of the rule, in ISO 8601 format.

**Q:** When should you update the `modified` date?
**A:** When changing the title, detection section, level, logsource (rare), or status to `deprecated`.

### LogSource

**Q:** What is the `logsource` section?
**A:** It describes the log data on which the detection is meant to be applied, including `category`, `product`, `service`, and `definition` attributes.

**Q:** How do you target Windows Security EventLog with a rule?
**A:** Use `logsource: product: windows / service: security`.

**Q:** What is the difference between `category`, `product`, and `service` in logsource?
**A:** `category` is a logical group (e.g., `firewall`, `antivirus`), `product` selects all logs of a product (e.g., `windows`), and `service` is a specific subset (e.g., `security`, `sshd`).

**Q:** Is `logsource` mandatory?
**A:** Yes. The `logsource` section is mandatory.

### Detection - Search-Identifier

**Q:** What is a search-identifier in the detection section?
**A:** It is a named definition (e.g., `selection`, `keywords`) that contains lists or maps representing properties of searches on log data.

**Q:** How do you structure a detection selection?
**A:** As a search-identifier containing either a list (strings or maps, linked with OR) or a map (key/value pairs, linked with AND).

### Detection - String Wildcard

**Q:** What wildcard characters can you use in Sigma strings?
**A:** `?` matches a single mandatory character, `*` matches an unbounded length string.

**Q:** How do you match `progA.exe`, `progB.exe`, etc. in a single expression?
**A:** Use `prog?.exe`.

**Q:** How do you match `antivirus_V1.exe`, `antivirus_V21.2.1.exe`, etc.?
**A:** Use `antivirus_V*.exe`.

### Detection - Escape Character

**Q:** How do you escape a wildcard character in Sigma?
**A:** Use the backslash `\` to escape `*` and `?` (e.g., `\*`, `\?`).

**Q:** If you want to match a literal `\*` (backslash followed by asterisk), how do you write it?
**A:** Use `\\*` — the first `\\` escapes the backslash, then `*` acts as wildcard. For a literal backslash and asterisk, use `\\\*`.

### Detection - Lists

**Q:** How are lists evaluated in the detection section?
**A:** Lists of strings are linked with logical OR — at least one value must match.

**Q:** Can a list contain maps instead of plain strings?
**A:** Yes. A list of maps links the map items with logical OR.

### Detection - Maps

**Q:** How are maps (key/value pairs) evaluated?
**A:** All key/value pairs in a map are linked with logical AND.

**Q:** How do you express an AND condition between multiple fields?
**A:** Put them as key/value pairs in the same search-identifier map (e.g., `EventLog: Security` AND `EventID: 4624`).

### Detection - Field Usage

**Q:** When should you use a mapped field name vs. the raw field name?
**A:** Use mapped field names if they exist in the taxonomy. For new/rarely used fields, use them as they appear in the log source, stripping all spaces.

**Q:** In Windows EventViewer, the field `New Value` appears — how should it be written in Sigma?
**A:** As `NewValue` (spaces stripped).

**Q:** How do you reference XML attributes in Windows event headers?
**A:** Link the tag and attribute names with an underscore, e.g., `Provider_Name` for `<Provider Name="...">`.

### Detection - Special Field Values

**Q:** How do you express an empty field value in Sigma?
**A:** Use `''` (empty string).

**Q:** How do you express a null field value?
**A:** Use `null`.

**Q:** Can `null` be part of a list of field values?
**A:** No. `null` is its own type and cannot share a list with other values.

**Q:** How do you express "field is not null"?
**A:** Create a selection with the field set to `null`, then negate it in the condition (e.g., `condition: selection and not filter`).

### Detection - Field Existence

**Q:** How do you check if a field exists in the log event?
**A:** Use the `exists` modifier with a boolean value, e.g., `PasswordLastSet|exists: true`.

**Q:** How can you detect that a field is absent from an event?
**A:** Use `PasswordLastSet|exists: false`.

### Detection - Value Modifiers

**Q:** What are value modifiers in Sigma?
**A:** They extend or modify how detection values are evaluated, appended after the field name with a pipe `|` separator.

**Q:** How do you chain multiple modifiers on a single field?
**A:** Separate them with pipe characters: `fieldname|mod1|mod2: value`. They are applied in the given order.

**Q:** What is the difference between a transformation modifier and a type modifier?
**A:** Transformation modifiers transform values (e.g., Base64 encoding); they are backend-agnostic. Type modifiers change how the value is handled by the backend (e.g., `re` for regex); they must be supported by the backend.

### Detection - Placeholders

**Q:** What are placeholders in Sigma?
**A:** Values that get their final meaning at conversion or usage time, enclosed in `%` signs (e.g., `%Servers%`).

**Q:** How do you use a placeholder value?
**A:** Apply the `expand` modifier: `field|expand: %name%`. Without `expand`, `%name%` is treated as a literal value.

**Q:** What is `%Administrators%` used for?
**A:** It is a standard placeholder for administrative user accounts.

**Q:** How do you write a literal percent character in a value?
**A:** Escape it with a backslash: `\%`.

### Detection - Keywords Search

**Q:** What is a keyword search in Sigma?
**A:** Searching across entire log events rather than specific fields, using a list under a search-identifier.

**Q:** How do you express an AND between keywords?
**A:** Use the `|all` modifier: `'|all': ['keyword1', 'keyword2']`.

**Q:** What search-identifier name is commonly used for keyword searches?
**A:** Simply `keywords` as a convention.

### Condition

**Q:** What is the `condition` field for?
**A:** It specifies which search-identifier(s) in the `detection` section must evaluate to `true` for the rule to fire.

**Q:** How do you express "selection1 OR (keywords1 AND keywords2)"?
**A:** Use brackets: `condition: selection1 or (keywords1 and keywords2)`.

**Q:** What is the operator precedence in Sigma conditions?
**A:** `or` (lowest), `and`, `not`, `x of search-identifier`, `( expression )` (highest).

**Q:** How do you use `all of them`?
**A:** It requires all defined search-identifiers (not starting with `_`) to match. Its use is discouraged — prefer `all of selection*`.

**Q:** What does `1 of selection*` do?
**A:** It matches if at least one search-identifier matching the pattern `selection*` evaluates to true.

**Q:** Can the condition be a list?
**A:** Yes. Each list item generates a separate query, and they are linked with OR.

### Fields

**Q:** What is the `fields` attribute for?
**A:** It lists log fields that should be displayed to the analyst for further analysis of the event.

**Q:** Which field helps the analyst by specifying what to display?
**A:** The `fields` attribute (optional).

### FalsePositives

**Q:** What is the `falsepositives` attribute for?
**A:** It lists known false positives that may occur when using the rule.

**Q:** Where should you document known benign triggers of a rule?
**A:** In the `falsepositives` field (optional).

### Level

**Q:** What severity levels are available in Sigma?
**A:** `informational`, `low`, `medium`, `high`, and `critical`. Each level describes the criticality of a triggered rule:
- `informational`: Enrichment/tagging only. No case or alerting should be triggered because a huge amount of events is expected to match.
- `low`: Notable event but rarely an incident. Low rated events can be relevant in high numbers or combination with others. Immediate reaction shouldn't be necessary, but a regular review is recommended.
- `medium`: Relevant event that should be reviewed manually on a more frequent basis.
- `high`: Relevant event that should trigger an internal alert and requires a prompt review.
- `critical`: Highly relevant event that indicates an incident. Critical events should be reviewed immediately. Used only for cases in which probability borders certainty.

**Q:** When should you use `critical` instead of `high`?
**A:** `critical` is for incidents where probability borders certainty and requires immediate review. `high` is for events that should trigger an internal alert and require a prompt review but may have slight uncertainty.

**Q:** What does the `informational` level mean?
**A:** The rule is intended for enrichment/tagging only (e.g., by tagging events). No case or alerting should be triggered because it is expected that a huge amount of events will match these rules.

**Q:** Which level indicates a rule is for enrichment only?
**A:** `informational`.

### Tags

**Q:** What are Sigma tags used for?
**A:** They categorize rules by attack techniques, target systems, event types, and other metadata.

**Q:** How do you tag a rule with a MITRE ATT&CK technique?
**A:** Use the format `attack.t1234` (e.g., `attack.t1059` for Command and Scripting Interpreter).

**Q:** What character set is allowed in tags?
**A:** Lowercase letters, numerals, underscores, and hyphens. No spaces. The dot is used as namespace separator.

### Scope

**Q:** What is the `scope` attribute?
**A:** A list of intended scopes for the rule, e.g., limiting a rule to server machines only.

**Q:** How do you limit a rule to only apply on Windows Server machines?
**A:** Add `scope: ['server']` to the rule.

---

## Filters Specification (sigma-filters-specification.md)

### Introduction

**Q:** What is a Sigma filter used for?
**A:** Filters exclude specific values or patterns from rule detection across multiple rules, enabling environment-specific tuning to suppress false positives.

**Q:** When would you use a meta-filter instead of editing each rule individually?
**A:** When the same exclusion applies to many rules (e.g., a valid GPO script triggering multiple Sigma rules), a single meta-filter is easier to maintain.

### File Structure

**Q:** What filename prefix is recommended for filter files?
**A:** The prefix `mf_` (e.g., `mf_exclude_admins.yml`).

**Q:** How should you name a meta-filter file?
**A:** Use the same conventions as Sigma rules: 10-70 chars, lowercase, `_` instead of spaces, `.yml` extension.

### Components - title / id

**Q:** What fields are mandatory in a filter rule?
**A:** `title`, `logsource`, `filter` (which contains `rules`, `selection`, and `condition`).

**Q:** Does a filter have a `level` or `status` field?
**A:** No. A filter has no `level` or `status` because its purpose is to enrich an existing Sigma rule.

### Global Filter - rules

**Q:** How does a filter reference which rules it applies to?
**A:** Using the `rules` attribute inside the `filter` section, listing rule IDs (UUIDs) with optional comments.

**Q:** What is the `rules` field inside `filter` for?
**A:** It refers to one or more Sigma rules where the filter should be applied.

### Global Filter - selection / condition

**Q:** How do you write the detection logic of a filter?
**A:** Using `selection` and `condition` inside the `filter` section, with the same syntax as rule detection.

**Q:** Does a filter use a `detection` section?
**A:** No. It uses `selection` and `condition` inside the `filter` attribute.

### Example

**Q:** Give an example of filtering out the local `adm_` administrator account.
**A:**
```yaml
title: Filter Administrator account
logsource:
    category: process_creation
    product: windows
filter:
    rules:
        - 6f3e2987-db24-4c78-a860-b4f4095a7095
    selection:
        User|startswith: 'adm_'
    condition: selection
```

---

## Correlation Rules Specification (sigma-correlation-rules-specification.md)

### Introduction

**Q:** Why do correlation rules exist in Sigma?
**A:** They allow detecting patterns across multiple events, rules, or data sources, enabling complex detections like brute-force or multi-step attack chains.

**Q:** When should you use a correlation rule instead of a simple Sigma rule?
**A:** When you need to link multiple events (e.g., X failed logins followed by a success, or event A and event B within the same time window).

### Compatibility

**Q:** What should happen if the target backend cannot support a correlation feature?
**A:** An error must be raised by the conversion backend if the unsupported feature is specified as must. A warning should be issued for "should" aspects.

**Q:** If the target system cannot recognize the order of temporal events, what should the backend do?
**A:** Issued a warning to raise the user's awareness about potential false positives.

### File Structure

**Q:** What filename prefix is recommended for correlation rules?
**A:** The prefix `mr_` (e.g., `mr_brute_force.yml`).

**Q:** How is a correlation rule file structured?
**A:** A dedicated YAML document with `title`, optional `id`, and a `correlation` section containing `type`, `rules`, etc.

### Correlation Type

**Q:** What correlation types are available in Sigma?
**A:** `event_count`, `value_count`, `temporal`, `temporal_ordered`, `value_sum`, `value_avg`, and `value_percentile`.

**Q:** How do you create a rule that requires events to occur in a specific order?
**A:** Use `type: temporal_ordered`.

**Q:** What correlation type detects events within a time window regardless of order?
**A:** `temporal`.

### Related Rules

**Q:** How do you reference detection rules in a correlation rule?
**A:** Using the `rules` attribute inside the `correlation` section, referencing rules by their `id` or `name`.

**Q:** Can `rules` accept human-readable names instead of UUIDs?
**A:** Yes, if the referenced rules have a `name` attribute defined. The tool must manage name-to-id translation automatically.

### Aliases

**Q:** What are field name aliases used for?
**A:** They allow aggregating across different field names from different event types (e.g., mapping `source.ip` in one rule and `destination.ip` in another to the same alias).

**Q:** How do you correlate events where the same IP appears as source in one event and destination in another?
**A:** Use the `aliases` attribute to define a common alias for the two different field names, then use that alias in `group-by`.

### Group-by

**Q:** What is the `group-by` attribute for?
**A:** It defines one or more fields that form the scope for counting or matching (e.g., count failed logins per user).

**Q:** How do you count failed logins grouped by user account?
**A:** Use `group-by: [TargetUserName]`.

**Q:** How are multiple fields in `group-by` linked?
**A:** They are linked with logical AND (e.g., group by unique "name/domain" pair).

### Timespan

**Q:** How do you define a time window in a correlation rule?
**A:** Use the `timespan` attribute with format `number + letter` (e.g., `5m`, `1h`, `30s`, `2d`).

**Q:** How do you write a 1-hour-30-minute timespan?
**A:** `timespan: 90m`.

### Condition (Correlation)

**Q:** What condition operators are available for correlation rules?
**A:** `gt` (greater than), `gte` (greater or equal), `lt` (less than), `lte` (less or equal), `eq` (equal), `neq` (not equal).

**Q:** How do you express a range condition like "between 101 and 200"?
**A:** Use a map of two operators:
```yaml
condition:
    gt: 100
    lte: 200
```

### Event Count (event_count)

**Q:** What does `event_count` do?
**A:** It counts events matching the referred rules within a timespan, grouped by `group-by` fields.

**Q:** How do you detect 100 or more failed logins to a host in one hour?
**A:**
```yaml
correlation:
    type: event_count
    rules:
        - failed_login_rule_id
    group-by:
        - ComputerName
    timespan: 1h
    condition:
        gte: 100
```

### Value Count (value_count)

**Q:** What does `value_count` do?
**A:** It counts distinct values in a specified `field`, grouped by `group-by` fields.

**Q:** How do you detect failed logins from more than 100 different user accounts in a day?
**A:**
```yaml
correlation:
    type: value_count
    rules:
        - failed_login_rule_id
    group-by:
        - ComputerName
    timespan: 1d
    condition:
        field: User
        gte: 100
```

**Q:** What extra attribute does `value_count` require compared to `event_count`?
**A:** A `field` attribute inside the `condition` section.

### Temporal Proximity (temporal)

**Q:** What does `temporal` correlation do?
**A:** It detects if all events defined by the referred rules occur within a timespan, with the same values in `group-by` fields.

**Q:** How do you detect three reconnaissance commands invoked within 5 minutes on the same system by the same user?
**A:**
```yaml
correlation:
    type: temporal
    rules:
        - recon_cmd_a
        - recon_cmd_b
        - recon_cmd_c
    group-by:
        - ComputerName
        - User
    timespan: 5m
```

### Ordered Temporal Proximity (temporal_ordered)

**Q:** What does `temporal_ordered` add beyond `temporal`?
**A:** It requires events to appear in the exact order specified in the `rules` attribute.

**Q:** How do you detect failed logins followed by a successful login by the same user within 10 minutes?
**A:**
```yaml
correlation:
    type: temporal_ordered
    rules:
        - multiple_failed_login
        - successful_login
    group-by:
        - User
    timespan: 10m
```

### Value Sum (value_sum)

**Q:** What does `value_sum` do?
**A:** It checks if the sum of a numeric field across matching events exceeds a threshold.

**Q:** How do you detect possible exfiltration where total bytes sent > 1,000,000 in one hour?
**A:**
```yaml
correlation:
    type: value_sum
    rules:
        - website_access
    group-by:
        - SourceIP
        - User
    timespan: 1h
    condition:
        field: bytes_sent
        gt: 1000000
```

### Value Average (value_avg)

**Q:** What does `value_avg` do?
**A:** It checks if the average of a numeric field across matching events exceeds a threshold.

**Q:** How do you detect suspicious average network traffic where average bytes out > 500 over 24 hours?
**A:**
```yaml
correlation:
    type: value_avg
    rules:
        - rule_a_id
    group-by:
        - SourceIP
        - User
    timespan: 24h
    condition:
        field: BytesOut
        gt: 500
```

### Value Percentile (value_percentile)

**Q:** What does `value_percentile` do?
**A:** It checks when a certain percentage of observed values occur (e.g., median is percentile 50).

**Q:** How do you detect a process name that appeared in less than 1% of all processes in the last 24 hours?
**A:**
```yaml
correlation:
    type: value_percentile
    rules:
        - process_creation
    group-by:
        - ComputerName
    timespan: 24h
    condition:
        field: image
        lte: 1
```

### Generate

**Q:** What does the `generate` attribute do?
**A:** It defines whether the rules referred by the correlation should also be converted as standalone rules (`generate: true`) or only the correlation query should be generated (default).

**Q:** How do you ensure that correlation sub-rules are also converted independently?
**A:** Set `generate: true` in the correlation rule.

---

## Modifiers Specification (sigma-appendix-modifiers.md)

### Generic Modifiers

**Q:** What does the `all` modifier do?
**A:** It changes list evaluation from OR to AND, requiring all values in a list to match.

**Q:** How do you express "command line must contain both 'param1' and 'param2' regardless of order"?
**A:** Use `CommandLine|all: ['param1', 'param2']`.

**Q:** Can `all` be used on a single-item list?
**A:** No. Single item values are not allowed to have the `all` modifier.

**Q:** What does `startswith` do?
**A:** It matches a value at the beginning of the field's content, replacing a wildcard like `adm*`.

**Q:** How do you avoid using `adm*` wildcard for matching admin accounts?
**A:** Use `User|startswith: 'adm'`.

**Q:** What does `endswith` do?
**A:** It matches a value at the end of the field's content, replacing a wildcard like `*\cmd.exe`.

**Q:** How do you express `*\cmd.exe` without manual wildcards?
**A:** Use `Image|endswith: '\cmd.exe'`.

**Q:** What does `contains` do?
**A:** It wraps the value with `*` wildcards, matching the value anywhere in the field.

**Q:** How do you search for a value anywhere in a field?
**A:** Use `field|contains: 'value'`.

**Q:** What does `exists` do?
**A:** It checks whether a certain field exists or does not exist in a log event, based on a boolean value.

**Q:** How do you verify if a field is present in an event?
**A:** Use `field|exists: true`.

**Q:** How do you check that a field does not exist?
**A:** Use `field|exists: false`.

**Q:** What does `cased` do?
**A:** It makes value matching case-sensitive. Default Sigma behavior is case-insensitive.

**Q:** How do you force case-sensitive matching?
**A:** Add the `cased` modifier: `field|cased: 'Value'`.

**Q:** What does `neq` do on a field?
**A:** It matches when the field is different from the specified value(s).

**Q:** How do you exclude a specific value from a selection?
**A:** Use `field|neq: 'excluded_value'`.

### String Modifiers

**Q:** What does `windash` do?
**A:** It generates all permutations of `-`, `/`, `–` (en dash), `—` (em dash), and `―` (horizontal bar) characters for Windows command-line flag matching.

**Q:** How do you match both `-flag` and `/flag` in Windows command lines?
**A:** Use `CommandLine|windash: 'flag'`.

### Regular Expression (re)

**Q:** What does the `re` modifier do?
**A:** It treats the value as a PCRE regular expression. Regex is case-sensitive by default.

**Q:** What regex flavor is supported by Sigma?
**A:** PCRE with a specific set of supported metacharacters: wildcards (`.`), anchors (`^`, `$`), quantifiers (`*`, `+`, `?`, `{n,m}`), character classes (`[a-z]`, `[^a-z]`), alternation (`|`), and grouping (`()`). Other metacharacters are **unsupported** and cannot be used.

**Q:** How do you enable case-insensitive regex matching?
**A:** Use the `i` sub-modifier: `field|re/i: 'pattern'`.

**Q:** What does `re/m` do?
**A:** Enables multi-line mode where `^` and `$` match the start/end of each line.

**Q:** What does `re/s` do?
**A:** Enables single-line mode where `.` matches all characters including newline.

### Encoding Modifiers

**Q:** What does the `base64` modifier do?
**A:** It Base64-encodes the detection value before matching.

**Q:** What does `base64offset` do?
**A:** It applies Base64 encoding with additional offsets (0-2 bytes) to handle values that may appear at different positions in a Base64 stream.

**Q:** What does `utf16le` do?
**A:** It transforms the value to UTF16-LE encoding (e.g., `cmd` → `63 00 6d 00 64 00`).

**Q:** What does `wide` do?
**A:** It is an alias for `utf16le`.

**Q:** What is the difference between `utf16le` and `utf16be`?
**A:** `utf16le` uses little-endian encoding, `utf16be` uses big-endian encoding.

**Q:** What does `utf16` do?
**A:** It prepends a Byte Order Mark (BOM) and encodes in UTF-16.

### Numeric Modifiers

**Q:** What numeric modifiers are available?
**A:** `lt` (less than), `lte` (less or equal), `gt` (greater than), `gte` (greater or equal), `neq` (not equal).

**Q:** How do you match a PID greater than 10000?
**A:** Use `ProcessId|gt: 10000`.

### Time Modifiers

**Q:** What time modifiers are available?
**A:** `minute` (0-59), `hour` (0-23), `day` (1-31), `week` (1-52), `month` (1-12), `year`.

**Q:** How do you extract the hour from a timestamp field?
**A:** Use `Timestamp|hour: 9` to match events at the 9th hour.

**Q:** Are time modifiers designed for timezone conversion?
**A:** No. They are not designed to handle timezone or format conversions.

### IP Modifiers (cidr)

**Q:** What does the `cidr` modifier do?
**A:** It enables CIDR network range matching for IP address fields, supporting both IPv4 and IPv6.

**Q:** How do you match any IP in the range 10.0.0.0/8?
**A:** Use `DestinationIp|cidr: 10.0.0.0/8`.

### Specific Modifiers

**Q:** What does the `expand` modifier do?
**A:** It enables placeholder expansion in values. Placeholders like `%Servers%` are replaced at conversion time.

**Q:** How do you use a placeholder in a rule?
**A:** Apply the `expand` modifier: `field|expand: '%Servers%'`.

**Q:** What does the `fieldref` modifier do?
**A:** It modifies a plain string into a field reference, allowing direct comparison between fields in matched events.

**Q:** How do you compare two fields directly at query time?
**A:** Use `fieldref`: `User|fieldref: 'TargetUser'` to compare the value of `User` with the value of `TargetUser`.

**Q:** Can `fieldref` be combined with `neq`?
**A:** Yes. `User|fieldref|neq: 'TargetUser'` matches when User differs from TargetUser.

---

## Tags Specification (sigma-appendix-tags.md)

### Namespaces - General

**Q:** What is a tag namespace in Sigma?
**A:** A prefix separated by a dot that organizes tags by source (e.g., `attack`, `cve`, `tlp`).

**Q:** What format do Sigma tags follow?
**A:** `namespace.value` (e.g., `attack.t1059`, `cve.2021-44228`, `tlp.amber`).

### Namespace: attack (MITRE ATT&CK)

**Q:** How do you tag a rule with a MITRE ATT&CK technique?
**A:** Use `attack.t` followed by the technique ID, e.g., `attack.t1059` for Command and Scripting Interpreter.

**Q:** What does `attack.g1234` refer to?
**A:** A MITRE ATT&CK group (e.g., APT group).

**Q:** What does `attack.s1234` refer to?
**A:** A MITRE ATT&CK software/tool.

**Q:** What does `attack.ds1234` refer to?
**A:** A MITRE ATT&CK data source.

**Q:** How do you tag a tactic like "Defense Evasion"?
**A:** Use `attack.defense-evasion`.

**Q:** What does `attack.m1234` refer to?
**A:** A MITRE ATT&CK mitigation.

**Q:** What does `attack.a1234` refer to?
**A:** A MITRE ATT&CK asset.

### Namespace: car

**Q:** What does the `car` namespace refer to?
**A:** MITRE Cyber Analytics Repository (CAR). Tags use the format `car.YYYY-MM-NNN` without the `CAR-` prefix.

**Q:** How do you tag a rule referencing CAR analytics ID 2016-04-005?
**A:** Use `car.2016-04-005`.

### Namespace: cve

**Q:** How do you tag a rule related to a specific CVE?
**A:** Use `cve.` followed by the CVE ID in lowercase with dots as separators, e.g., `cve.2021-44228`.

**Q:** What tag format links a rule to the Log4Shell vulnerability?
**A:** `cve.2021-44228`.

### Namespace: d3fend

**Q:** What does the `d3fend` namespace refer to?
**A:** MITRE D3FEND, a knowledge graph of cybersecurity countermeasure techniques.

**Q:** How do you tag a D3FEND technique like Access Modeling?
**A:** Use `d3fend.d3-am` (technique) or `d3fend.d3f-WindowsNtOpenFile` (artifact).

### Namespace: detection

**Q:** What are the supported detection type tags?
**A:** `detection.dfir`, `detection.emerging-threats`, `detection.threat-hunting`.

**Q:** How do you mark a rule as intended for threat hunting?
**A:** Add the tag `detection.threat-hunting`.

### Namespace: stp (Summiting the Pyramid)

**Q:** What does the `stp` namespace define?
**A:** The detection analytic robustness score according to the MITRE Summiting the Pyramid scheme.

**Q:** What does `stp.4` indicate?
**A:** An analytic robustness score of 4 (out of 5).

**Q:** What does `stp.3k` indicate?
**A:** An analytic robustness of 3 and event robustness of Kernel-mode (the highest level).

### Namespace: tlp (Traffic Light Protocol)

**Q:** What TLP tags are supported?
**A:** `tlp.red`, `tlp.amber`, `tlp.amber-strict`, `tlp.green`, `tlp.clear`.

**Q:** How do you protect a sensitive rule from broad distribution?
**A:** Add `tlp.red` to restrict sharing to individual recipients only.

---

## Taxonomy Specification (sigma-appendix-taxonomy.md)

### Log Sources - General

**Q:** What does the Sigma taxonomy define?
**A:** It defines the allowed field names and log sources (category/product/service) for Sigma rules shared on the official SigmaHQ repository.

**Q:** How are log sources organized?
**A:** By directory structure (application, category, cloud, linux, macos, network, product, windows), mirroring the SigmaHQ rules repository.

### Application Folder

**Q:** How do you write the logsource for a Django application rule?
**A:** `category: application, product: django`.

**Q:** What category is used for application-level rules?
**A:** `category: application`.

**Q:** How do you write the logsource for a Python application rule?
**A:** `category: application, product: python`.

### Category Folder

**Q:** What does `category: antivirus` mean without a product?
**A:** It targets antivirus detection messages regardless of the specific product.

**Q:** What logsource targets SQL query logs?
**A:** `category: database`.

### Cloud Folder

**Q:** How do you target AWS CloudTrail logs?
**A:** `product: aws, service: cloudtrail`.

**Q:** How do you target Azure Sign-in logs?
**A:** `product: azure, service: signinlogs`.

**Q:** What logsource targets GCP audit logs?
**A:** `product: gcp, service: gcp.audit`.

**Q:** How do you write a logsource for GitHub audit logs?
**A:** `product: github, service: audit`.

### Linux Folder

**Q:** How do you target Linux auditd logs?
**A:** `product: linux, service: auditd`.

**Q:** What logsource targets SSH daemon logs on Linux?
**A:** `product: linux, service: sshd`.

### Windows Folder

**Q:** How do you target the Windows Security EventLog?
**A:** `product: windows, service: security`.

**Q:** How do you target Sysmon process creation events?
**A:** `category: process_creation, product: windows`.

**Q:** What logsource targets Windows PowerShell operational logs?
**A:** `product: windows, service: powershell-operational`.

**Q:** What is the difference between `service: security` and `service: sysmon`?
**A:** `security` targets the Windows Security EventLog (Event ID 4624, 4625, etc.), while `sysmon` targets Sysmon events (Event ID 1, 3, etc.).

### Network Events

**Q:** How do you target firewall logs?
**A:** `category: firewall` (optionally with a product like `product: windows` for Windows Firewall).

**Q:** What logsource targets Zeek network analysis logs?
**A:** `product: zeek, service: <specific_service>` (e.g., `conn`, `dns`, `http`).

### Fields - Generic

**Q:** What field name should you use for the process command line?
**A:** `CommandLine` (in the default Sigma taxonomy).

**Q:** What is the standard field for process image path?
**A:** `Image`.

**Q:** What is the standard field for the parent process image?
**A:** `ParentImage`.

**Q:** What field name captures the process ID?
**A:** `ProcessId`.

**Q:** What field captures the user or account name?
**A:** `User`.

### Root-level Fields

**Q:** What field contains the event identifier (numeric)?
**A:** `EventID`.

**Q:** What field contains the name of the log or channel?
**A:** `EventLog`.

**Q:** What field contains the severity or level of the event?
**A:** `EventLevel`.