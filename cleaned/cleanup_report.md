# Column Cleanup Report

Settings: min-fill threshold = 10.0% (columns with less data were dropped); empty property cells filled with 'NULL'.

| File | Rows In | Rows Out | Total Cols | Kept Cols | Dropped Cols | Cells Filled | Placeholders Cleared |
|---|---|---|---|---|---|---|---|
| Abuse Techniques.csv | 252 | 252 | 29 | 9 | 20 | 551 | 0 |
| Media characters.csv | 51 | 51 | 8 | 6 | 2 | 4 | 0 |
| Mental processes.csv | 27 | 26 | 11 | 8 | 3 | 57 | 0 |
| Player typologies.csv | 37 | 36 | 24 | 18 | 6 | 46 | 0 |
| Red flags.csv | 141 | 141 | 11 | 8 | 3 | 110 | 0 |
| Trauma.csv | 80 | 80 | 12 | 6 | 6 | 122 | 0 |
| Universal Neurological Encoding system.csv | 57 | 57 | 21 | 12 | 9 | 54 | 0 |
| Vulnerability Traits.csv | 91 | 91 | 11 | 8 | 3 | 144 | 0 |

## Files written

| Original file | Saved as |
|---|---|
| Abuse Techniques 6bf57ce301ad4bbfa6b2b9b192eafc97_all.csv | Abuse Techniques.csv |
| Media characters 97ab254eada34020beae74df3e251266_all.csv | Media characters.csv |
| Mental processes 1d2c418c9c4246fcbb88ae53c170930d_all.csv | Mental processes.csv |
| Player typologies 6f47a330da3743379ee546cf29e3b421_all.csv | Player typologies.csv |
| Red flags b77ae4bede5e4c3c8924b674a13e9370_all.csv | Red flags.csv |
| Trauma a79d6f244b72405fb6841d0f9757de1e_all.csv | Trauma.csv |
| Universal Neurological Encoding system 19aee3e2472c80e4937bec967dba15bf_all.csv | Universal Neurological Encoding system.csv |
| Vulnerability Traits 61fe931348ee478a85de56608cae8dfb_all.csv | Vulnerability Traits.csv |

## Dropped Columns Detail

**Abuse Techniques.csv**:
- 'Abuse Move-Trauma Research DOi' (0/252 filled)
- 'Abuse Quotes' (0/252 filled)
- 'Cleanup flag' (12/252 filled)
- 'Cleanup note' (14/252 filled)
- 'Comebacks' (1/252 filled)
- 'Data Links' (0/252 filled)
- 'Diamond Shield Example Lines' (1/252 filled)
- 'Diamond Shield Findings' (1/252 filled)
- 'Diamond Shield Principles' (0/252 filled)
- 'Diamond Shield Social Media' (1/252 filled)
- 'Emotions' (0/252 filled)
- 'Link to Trauma' (0/252 filled)
- 'Logical fallacies' (12/252 filled)
- 'Name 1' (0/252 filled)
- 'Select (1)' (0/252 filled)
- 'Social Media Topics' (1/252 filled)
- 'Social Media Topics 1' (0/252 filled)
- 'Summary of Trauma Research' (0/252 filled)
- 'Academic studies' (7/252 filled)
- 'Brain biases' (0/252 filled)

**Media characters.csv**:
- 'Cleanup flag' (1/51 filled)
- 'Cleanup note' (4/51 filled)

**Mental processes.csv**:
- 'Cleanup flag' (0/26 filled)
- 'Data Links' (0/26 filled)
- 'Tags' (0/26 filled)

**Player typologies.csv**:
- 'Abuse Quotes' (0/36 filled)
- 'Cleanup flag' (0/36 filled)
- 'Cleanup note' (0/36 filled)
- 'Comebacks' (0/36 filled)
- 'Emotions' (0/36 filled)
- 'Research' (1/36 filled)

**Red flags.csv**:
- 'Cleanup flag' (0/141 filled)
- 'Data Links' (0/141 filled)
- 'Emotions' (0/141 filled)

**Trauma.csv**:
- 'Cleanup flag' (1/80 filled)
- 'Cleanup note' (3/80 filled)
- 'Data Links' (2/80 filled)
- 'Frontline Findings' (1/80 filled)
- 'Quotes' (0/80 filled)
- 'Research' (0/80 filled)

**Universal Neurological Encoding system.csv**:
- 'Cleanup flag' (0/57 filled)
- 'Cleanup note' (0/57 filled)
- 'Comebacks' (0/57 filled)
- 'Data Links' (0/57 filled)
- 'Diamond Shield Findings' (0/57 filled)
- 'Diamond Shield Principles' (0/57 filled)
- 'Expert' (0/57 filled)
- 'Research' (1/57 filled)
- 'Sample Questions' (0/57 filled)

**Vulnerability Traits.csv**:
- 'Abuse Quotes' (0/91 filled)
- 'Data Links' (0/91 filled)
- 'Diamond Shield Findings' (0/91 filled)


# Structural checks

Every individual finding is in `cleanup_issues.csv`. Relationship checks are done by the loader.

| Check | Findings | What it means |
|---|---|---|
| Rows with no name | 2 | dropped from the cleaned file |
| Duplicate names | 3 | rows with the same name merge into one node |
| Empty descriptions | 356 | left blank on purpose; write one or remove the row |
| Very short descriptions | 12 | often placeholders; semantic search is weak on them |
| Reused descriptions | 0 | different rows share identical text; check for copy-paste |
| Duplicate column titles | 0 | values of the earlier column are lost |
| Files with no Name column | 0 | the first column was used as the name |
| Files with no rows | 0 | nothing to load |

## Empty descriptions by file

| File | Rows without a description | Of | Note |
|---|---|---|---|
| Media characters | 26 | 51 |  |
| Mental processes | 14 | 26 |  |
| Player typologies | 2 | 36 |  |
| Red flags | 141 | 141 | no description column in this file |
| Trauma | 80 | 80 | no description column in this file |
| Universal Neurological Encoding system | 3 | 57 |  |
| Vulnerability Traits | 90 | 91 |  |

## Duplicate names

- Media characters line 20: 'Tony Stark/Iron Man' 2 rows share this name (lines 20, 37); a loader keeps only one
- Trauma line 60: 'Loss of autonomy in decision-making' 2 rows share this name (lines 60, 61); a loader keeps only one
- Vulnerability Traits line 83: 'Empathic women who over-accommodate' 2 rows share this name (lines 83, 84); a loader keeps only one

## Rows with no name (dropped)

- Mental processes line 27: row has no name; dropped
- Player typologies line 35: row has no name; dropped

## Very short descriptions

- Abuse Techniques line 237: 'power transfer through financial dependence' 7 characters: 'Comment'
- Abuse Techniques line 238: 'Minimizing due to misunderstanding Literal communication mistaken as coldness Misreading emotional needs' 7 characters: 'Comment'
- Abuse Techniques line 240: 'Emotional flatness Reduced responsiveness Avoidance of heavy topics due to stress' 7 characters: 'Comment'
- Abuse Techniques line 241: 'Inattention / forgetfulness Emotional misattunement Overdependence on partner's structure' 7 characters: 'Comment'
- Abuse Techniques line 242: 'Boundary' 7 characters: 'Comment'
- Abuse Techniques line 244: 'Avoidance or shutdown when overwhelmed' 7 characters: 'Comment'
- Abuse Techniques line 245: 'Over-rationalizing feelings (“Let’s be practical about this.”)' 7 characters: 'Comment'
- Abuse Techniques line 246: 'Assuming everything is fine because he feels fine' 7 characters: 'Comment'
- Abuse Techniques line 247: 'Defaulting to solutions instead of empathy' 7 characters: 'Comment'
- Abuse Techniques line 250: 'Punitive conditioning' 7 characters: 'Comment'
- ...and 2 more in cleanup_issues.csv
