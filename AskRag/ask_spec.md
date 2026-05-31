# Sigma Specification Q/A

## Rules Specification

### Basic Rule Structure
**Q:** What are the required fields for a Sigma rule?  
**A:** The required fields are `title`, `status`, `logsource`, and `detection`.

**Q:** What is the purpose of the `description` field in a Sigma rule?  
**A:** The `description` field provides additional context, explanation, or author notes about the rule. It is optional.

**Q:** What are the possible values for the `status` field?  
**A:** The `status` field can be `production`, `test`, `experimental`, or `deprecated`.

### Logsource
**Q:** What fields are required in the `logsource` section?  
**A:** At least one of `product`, `service`, or `definition` must be specified. However, `product` and `service` together define the minimum logsource.

**Q:** How does logsource matching work in Sigma?  
**A:** Logsource matching uses a hierarchical approach. A rule matches if the event logsource contains at least all the fields specified in the rule's logsource section, with additional fields allowed.

### Detection Section
**Q:** What is the structure of the `detection` section?  
**A:** The `detection` section contains one or more arbitrary sections (keywords) that evaluate to boolean values. At least one keyword must evaluate to `true` for the rule to trigger.

**Q:** How are keyword lists evaluated in the detection section?  
**A:** Keyword lists (arrays) are evaluated with a logical OR — at least one value in the list must match.

**Q:** What are fixed strings in Sigma rules?  
**A:** Fixed strings are plain string values that are matched literally in log data.

**Q:** What are regular expressions in Sigma rules?  
**A:** Regular expressions are patterns enclosed in double forward slashes (`//`) that enable flexible string matching in log data.

### Condition
**Q:** What is the purpose of the `condition` field?  
**A:** The `condition` field specifies which keyword(s) in the `detection` section must evaluate to `true` for the rule to fire.

**Q:** What are the valid condition operators?  
**A:** Valid operators include `all` (all keywords must be true), `any` (at least one keyword must be true), and `1 of them` (at least one of the specified keywords must be true).

**Q:** Can conditions reference specific keywords by name?  
**A:** Yes, conditions can reference specific keywords by name, e.g., `condition: keyword1 or keyword2`.

### Level and Priority
**Q:** What levels are supported in Sigma rules?  
**A:** The supported levels are `info`, `low`, `medium`, `high`, `critical`, and `fatal`.

**Q:** How does the level field map to priority?  
**A:** The `level` field determines the severity/priority of the detected event for alerting and triage purposes.

## Filters Specification

**Q:** What are Sigma filters used for?  
**A:** Filters are used to exclude specific values or patterns from rule detection, allowing rules to be applied selectively.

**Q:** What is the structure of a filter rule?  
**A:** A filter rule requires `title`, `filter` (the filter conditions), `logsource`, and `rule` (reference to the rule being filtered).

**Q:** How are multiple filter values specified?  
**A:** Multiple filter values are specified as a list (array) within the filter section, using logical OR.

## Correlation Rules Specification

**Q:** What are correlation rules used for?  
**A:** Correlation rules detect patterns across multiple events, rules, or data sources that may indicate security incidents.

**Q:** What is the `type` field used for in correlation rules?  
**A:** The `type` field specifies the correlation method, such as `eventual`, `sequential`, `temporal`, `static`, or `aggregation`.

**Q:** What is the difference between `rules` and `rule` in correlation rules?  
**A:** The `rules` field references multiple rules for comparison, while `rule` references a single rule.

**Q:** What is the `group-by` field used for in aggregation correlation?  
**A:** The `group-by` field specifies which fields to group events by when performing aggregation correlation.

**Q:** What is the `count` condition used for?  
**A:** The `count` condition defines the minimum number of matching events required to trigger the correlation rule.

### Correlation Methods

**Q:** What is a `sequential` correlation?  
**A:** A sequential correlation detects events that occur in a specific order within a defined time window.

**Q:** What is a `temporal` correlation?  
**A:** A temporal correlation detects events that occur within a specific time window, regardless of order.

**Q:** What is a `static` correlation?  
**A:** A static correlation matches against static data values (e.g., known bad IPs, file hashes) defined in the rule.

## Modifiers Specification

### Value Modifiers
**Q:** What is the purpose of value modifiers in Sigma?  
**A:** Value modifiers extend or modify how detection values are evaluated against log data.

**Q:** What does the `cidr` modifier do?  
**A:** The `cidr` modifier enables CIDR (Classless Inter-Domain Routing) notation matching for IP address networks.

**Q:** How is CIDR notation written in Sigma rules?  
**A:** CIDR notation is specified as `value/mod:cir`, e.g., `192.168.0.0/16`.

**Q:** What does the `re` modifier do?  
**A:** The `re` modifier enables regular expression matching for the specified value.

**Q:** What does the `wi` modifier do?  
**A:** The `wi` modifier enables word boundary matching, ensuring the value matches whole words only.

**Q:** What does the `all` modifier do?  
**A:** The `all` modifier requires all occurrences of a value to match (as opposed to default any/first match).

### Field Modifiers
**Q:** What does the `field_name` modifier do?  
**A:** The `field_name` modifier changes the field name to match against in the log data.

**Q:** What does the `base64` modifier do?  
**A:** The `base64` modifier applies Base64 encoding to the detection value before matching.

**Q:** What does the `base64offset` modifier do?  
**A:** The `base64offset` modifier applies Base64 encoding with an additional offset to the detection value.

**Q:** What does the `cidr` modifier work with?  
**A:** The `cidr` modifier works with IP address fields and enables network range matching.

## Tags Specification

**Q:** What are Sigma tags used for?  
**A:** Sigma tags are used to categorize and classify rules by attack techniques, target systems, event types, and other metadata.

**Q:** How are tags structured in Sigma rules?  
**A:** Tags are specified as a list under the `tags` field at the rule level, using the format `tactic.name` or `technique.name`.

**Q:** What are the tag categories?  
**A:** Tags are organized by category: attack tactics, attack techniques, target systems, event categories, product/vendor, and more.

**Q:** How do tags relate to MITRE ATT&CK?  
**A:** Many tags follow the MITRE ATT&CK naming convention, enabling mapping between Sigma rules and ATT&CK techniques.

## Taxonomy Specification

**Q:** What is the Sigma taxonomy?  
**A:** The Sigma taxonomy defines the structured naming conventions and categories for Sigma tags, ensuring consistency across rules.

**Q:** How are taxonomy categories organized?  
**A:** Categories are organized hierarchically by type (tactics, techniques, systems, etc.) with subcategories.

**Q:** What is the purpose of the `platform` taxonomy?  
**A:** The platform taxonomy categorizes rules by target operating system or platform (e.g., `windows`, `linux`, `aws`, `azure`, `gcp`).

**Q:** How does the taxonomy support rule discoverability?  
**A:** The taxonomy provides standardized tags that enable searching, filtering, and organizing rules by technique, tactic, platform, or other criteria.
