# Column Cleanup Report

Settings: min-fill threshold = 10.0% (columns with less data were dropped); empty property cells filled with 'NULL'.

| File | Rows In | Rows Out | Total Cols | Kept Cols | Dropped Cols | Cells Filled |
|---|---|---|---|---|---|---|
| Abuse Techniques.csv | 252 | 252 | 29 | 9 | 20 | 551 |
| Media characters.csv | 51 | 51 | 8 | 6 | 2 | 30 |
| Mental processes.csv | 27 | 26 | 11 | 8 | 3 | 71 |
| Player typologies.csv | 37 | 36 | 24 | 18 | 6 | 46 |
| Red flags.csv | 141 | 141 | 11 | 8 | 3 | 110 |
| Trauma.csv | 80 | 80 | 12 | 6 | 6 | 122 |
| Universal Neurological Encoding system.csv | 57 | 57 | 21 | 12 | 9 | 54 |
| Vulnerability Traits.csv | 91 | 91 | 11 | 8 | 3 | 144 |

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


## Rows with an empty description (left blank on purpose)

import.py rejects empty descriptions. Write a real description or remove the row.

- Player typologies.csv: 'Mentally Ill'
- Player typologies.csv: 'Suspicious Strategist'
- Universal Neurological Encoding system.csv: 'Impulsivity-low'
- Universal Neurological Encoding system.csv: 'Sense of Self-low'
- Universal Neurological Encoding system.csv: 'isolation-high'
- Vulnerability Traits.csv: 'Trusting'
- Vulnerability Traits.csv: 'Open/Curious'
- Vulnerability Traits.csv: 'Tolerant'
- Vulnerability Traits.csv: 'Cooperative'
- Vulnerability Traits.csv: 'Agreeable'
- Vulnerability Traits.csv: 'Empathatic'
- Vulnerability Traits.csv: 'Loyal'
- Vulnerability Traits.csv: 'Low self esteem'
- Vulnerability Traits.csv: 'Neurotic'
- Vulnerability Traits.csv: 'Conscientious'
- Vulnerability Traits.csv: 'Straightforward/genuine'
- Vulnerability Traits.csv: 'Nonassertive'
- Vulnerability Traits.csv: 'Perfectionist'
- Vulnerability Traits.csv: 'PTSD'
- Vulnerability Traits.csv: 'Borderline Personality Disorder'
- Vulnerability Traits.csv: 'Depression'
- Vulnerability Traits.csv: 'Anxiety Disorder'
- Vulnerability Traits.csv: 'Substance Abuse Disorder'
- Vulnerability Traits.csv: 'Eating Disorder'
- Vulnerability Traits.csv: 'Schizophrenia'
- Vulnerability Traits.csv: 'Bipolar Disorder'
- Vulnerability Traits.csv: 'Obsessive-Compulsive Disorder'
- Vulnerability Traits.csv: 'Childhood abuse or neglect'
- Vulnerability Traits.csv: 'Sexual assault or rape'
- Vulnerability Traits.csv: 'Domestic violence'
- Vulnerability Traits.csv: 'Witnessing violence or trauma'
- Vulnerability Traits.csv: 'Significant loss or bereavement'
- Vulnerability Traits.csv: 'Chronic illness or disability'
- Vulnerability Traits.csv: 'Combat or other traumatic events experienced in adulthood'
- Vulnerability Traits.csv: 'Isolation'
- Vulnerability Traits.csv: 'Financial difficulty'
- Vulnerability Traits.csv: 'Recent Life Changes'
- Vulnerability Traits.csv: 'Lack of social support'
- Vulnerability Traits.csv: 'Currently searching for answers or meaning in life'
- Vulnerability Traits.csv: 'Lack of relationship experience'
- Vulnerability Traits.csv: 'ADHD'
- Vulnerability Traits.csv: 'Traumatic brain injuries'
- Vulnerability Traits.csv: 'Cognitive impairments'
- Vulnerability Traits.csv: 'Soul mates'
- Vulnerability Traits.csv: 'Believing in spiritual healing'
- Vulnerability Traits.csv: 'Likes highly masculine men'
- Vulnerability Traits.csv: 'Dependent mentality'
- Vulnerability Traits.csv: 'Ignoring red flags'
- Vulnerability Traits.csv: 'People-pleasing'
- Vulnerability Traits.csv: 'Insecurity'
- Vulnerability Traits.csv: 'Self-doubt'
- Vulnerability Traits.csv: 'Need validation/approval from others'
- Vulnerability Traits.csv: 'Fear of abandonment'
- Vulnerability Traits.csv: 'Fantasy-prone thinking'
- Vulnerability Traits.csv: 'Idealization'
- Vulnerability Traits.csv: 'Boundary issues'
- Vulnerability Traits.csv: 'Overconfidence in ability to be conned/spot liars'
- Vulnerability Traits.csv: '“Love will conquer all”'
- Vulnerability Traits.csv: '“Evil is a thing I will recognize”'
- Vulnerability Traits.csv: 'Altruism'
- Vulnerability Traits.csv: 'High relationship investment and high attachment'
- Vulnerability Traits.csv: 'Hyper-focus on sentimental aspects of a relationship'
- Vulnerability Traits.csv: 'Low impulsiveness'
- Vulnerability Traits.csv: 'High resourcefulness'
- Vulnerability Traits.csv: 'Magical thinking'
- Vulnerability Traits.csv: 'Optimistic'
- Vulnerability Traits.csv: 'Intellectualizing feelings'
- Vulnerability Traits.csv: 'Centers men; needs a relationship'
- Vulnerability Traits.csv: 'Unemployed or underemployed'
- Vulnerability Traits.csv: 'IPV within the social network'
- Vulnerability Traits.csv: 'Being bisexual'
- Vulnerability Traits.csv: 'Being non-hetero'
- Vulnerability Traits.csv: 'Being divorced or separated'
- Vulnerability Traits.csv: 'Ethnic minority background'
- Vulnerability Traits.csv: 'Experience being bullied in school'
- Vulnerability Traits.csv: 'Younger women under 30'
- Vulnerability Traits.csv: 'Elderly'
- Vulnerability Traits.csv: 'Lower education level'
- Vulnerability Traits.csv: 'High Tolerance for Ambivalence and Uncertainty'
- Vulnerability Traits.csv: 'Attachment difficulties'
- Vulnerability Traits.csv: 'Love = sacrifice'
- Vulnerability Traits.csv: 'Hyperindependence as a defense mechanism'
- Vulnerability Traits.csv: 'Wanting to be perceived as “good”'
- Vulnerability Traits.csv: 'Is an immigrant, documented or undocumented'
- Vulnerability Traits.csv: 'Has a need for closure'
- Vulnerability Traits.csv: 'Empathic women who over-accommodate'
- Vulnerability Traits.csv: 'Empathic women who over-accommodate'
- Vulnerability Traits.csv: 'Women who take responsibility for emotional labor'
- Vulnerability Traits.csv: 'Women who believe they can “teach” someone to be emotionally available'
- Vulnerability Traits.csv: 'Caretaker personalities'
- Vulnerability Traits.csv: 'Highly intuitive women who sense potential'
- Vulnerability Traits.csv: 'The Empath'
- Vulnerability Traits.csv: 'The Over-Giver'
- Vulnerability Traits.csv: 'The Peacemaker'
- Vulnerability Traits.csv: 'The Fixer'
