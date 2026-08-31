# Domain Schema

## Assigned domain

Grocery supply and recall notices (DOMAIN_ID 3)

## Entity

The form records a **grocery recall notice**.

| Field | Form control | Required | Description |
| --- | --- | --- | --- |
| `productName` | Text input | Yes | Name of the recalled grocery product |
| `brandName` | Text input | Yes | Brand or manufacturer name |
| `submitterEmail` | Email input | Yes | Email of the person submitting the notice |
| `recallDetails` | Textarea | Yes | Description of the issue, affected lots, and consumer guidance |
| `category` | Select | Yes | Grocery category for the affected product |
| `termsAccepted` | Checkbox | Yes | Confirms agreement to the terms and conditions |

## Category values

1. Produce
2. Meat and Seafood
3. Dairy and Refrigerated
4. Packaged Foods

## Example input

- Product name: Garden Fresh Spinach 10 oz
- Brand name: Valley Harvest
- Submitter email: recalls@example.edu
- Category: Produce
- Recall details: Selected bags may contain undeclared almonds. Consumers with nut allergies should not eat the product and should return it.

