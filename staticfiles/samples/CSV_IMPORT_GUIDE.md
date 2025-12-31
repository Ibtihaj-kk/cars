# Product CSV Import Guide

## CSV File Format

Your CSV file must include the following columns in this order:

| Column | Required | Format | Description | Example |
|--------|----------|--------|-------------|---------|
| `name` | ✅ Yes | Text | Product name | "Front Brake Pads" |
| `sku` | ✅ Yes | Text (unique) | Stock Keeping Unit | "BRK-001" |
| `category` | ✅ Yes | Text | Product category name | "Brakes" |
| `brand` | ✅ Yes | Text | Brand name | "Brembo" |
| `price` | ✅ Yes | Number (decimal) | Price in original currency | "100.00" |
| `original_currency` | ⚠️ Optional | 3-letter code | Currency code (ISO 4217) | "GBP" |
| `quantity` | ✅ Yes | Integer | Stock quantity | "50" |
| `description` | ⚠️ Optional | Text | Product description | "High performance ceramic brake pads" |
| `image_url` | ⚠️ Optional | URL | Product image URL | "https://example.com/image.jpg" |

---

## Currency Codes Supported

When specifying the `original_currency` column, use one of these 3-letter currency codes:

- **USD** - US Dollar (default if not specified)
- **SAR** - Saudi Riyal
- **AED** - UAE Dirham
- **GBP** - British Pound Sterling
- **EUR** - Euro
- **QAR** - Qatari Riyal
- **KWD** - Kuwaiti Dinar
- **OMR** - Omani Rial
- **BHD** - Bahraini Dinar
- **EGP** - Egyptian Pound
- **JOD** - Jordanian Dinar

**Important:**
- If `original_currency` is not provided, system defaults to **USD**
- Currency codes must be exactly 3 letters (case-insensitive)
- Invalid currency codes default to **USD**

---

## Example CSV

```csv
name,sku,category,brand,price,original_currency,quantity,description,image_url
Front Brake Pads,BRK-001,Brakes,Brembo,100.00,GBP,50,High performance ceramic brake pads,https://example.com/brake-pads.jpg
Oil Filter,FLT-002,Filters,Mann,25.00,USD,100,Premium oil filter,https://example.com/oil-filter.jpg
Air Filter,FLT-003,Filters,K&N,168.75,SAR,75,High-flow air filter,https://example.com/air-filter.jpg
```

---

## Import Behavior

### Creating New Products
- Products are created with the price in the specified currency
- System automatically converts prices for display in user's preferred currency
- Example: Price of 100 GBP displays as ~﷼476 SAR for Saudi users

### Updating Existing Products
- Existing products are matched by SKU or name
- Price and currency are updated together
- Quantity is updated to new value

### Validation
- ✅ Required fields must be present
- ✅ Price must be valid decimal number
- ✅ Quantity must be valid integer
- ✅ SKU must be unique (no duplicates in same import)
- ✅ Currency code validated (defaults to USD if invalid)

---

## Tips for Successful Import

1. **Use UTF-8 encoding** for your CSV file
2. **Test with small batch** (5-10 products) first
3. **Unique SKUs** - ensure each product has unique SKU
4. **Valid numbers** - no currency symbols in price column (just the number)
5. **Category/Brand auto-creation** - if category or brand doesn't exist, it will be created automatically
6. **Currency consistency** - you can mix currencies in the same import file

---

## Download Sample

[Download Sample CSV](../samples/parts_import_sample.csv) - Ready-to-use template with example products
