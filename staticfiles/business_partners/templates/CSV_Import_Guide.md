# Vendor Parts Bulk Import CSV Guide

## Overview
This guide explains how to use the CSV template for bulk importing vendor parts into the Cars Portal system. The template includes all available fields from the comprehensive parts management system.

## CSV Template Structure

### Required Fields (Must be provided)
- **parts_number**: Unique identifier for the part (max 50 characters)
- **material_description**: Short description of the part (max 200 characters)
- **base_unit_of_measure**: Unit of measure (EA, KG, L, etc.)
- **category_name**: Category name (must exist in system)
- **brand_name**: Brand name (must exist in system)
- **price**: Selling price (decimal with 2 places)

### Basic Information Fields
- **material_description_ar**: Arabic description (optional, max 200 characters)
- **gross_weight**: Gross weight in kg (decimal with 3 places)
- **net_weight**: Net weight in kg (decimal with 3 places)
- **size_dimensions**: Physical dimensions (max 100 characters)
- **manufacturer_part_number**: Manufacturer's part number (max 40 characters)
- **manufacturer_oem_number**: OEM number (max 50 characters)
- **image_url**: URL to part image (optional)
- **warranty_period**: Warranty period in months (integer)

### Inventory Management Fields
- **quantity**: Current stock quantity (integer)
- **safety_stock**: Safety stock level (integer)
- **minimum_safety_stock**: Minimum safety stock (integer)
- **reorder_point**: Reorder point threshold (integer)
- **minimum_order_quantity**: Minimum order quantity (integer)
- **inventory_threshold**: Low stock alert threshold (integer)

### Storage & Location Fields
- **plant**: Plant code (max 50 characters)
- **storage_location**: Storage location code (max 50 characters)
- **storage_location_code**: Detailed storage location (max 50 characters)
- **warehouse_number**: Warehouse identifier (max 50 characters)
- **storage_bin**: Storage bin location (max 50 characters)

### Advanced Fields
- **material_type**: Material type classification (max 50 characters)
- **material_group**: Material group code (max 50 characters)
- **division**: Division code (max 50 characters)
- **external_material_group**: External material group (max 50 characters)
- **old_material_number**: Legacy part number (max 50 characters)
- **expiration_xchpf**: Expiration date (YYYY-MM-DD format)
- **abc_indicator**: ABC classification (A, B, or C)

### Pricing Fields
- **standard_price**: Standard price (decimal with 2 places)
- **moving_average_price**: Moving average price (decimal with 2 places)
- **cost_price**: Cost price for profit calculation (decimal with 2 places)
- **price_unit_peinh**: Price unit indicator (integer)
- **valuation_class**: Valuation class code (max 50 characters)
- **price_control_indicator**: Price control method (max 10 characters)

### Planning & MRP Fields
- **planned_delivery_time_days**: Planned delivery time in days (integer)
- **goods_receipt_processing_time_days**: GR processing time in days (integer)
- **mrp_type**: MRP type code (max 10 characters)
- **mrp_group**: MRP group code (max 10 characters)
- **mrp_controller**: MRP controller code (max 10 characters)

### Status Fields
- **is_active**: Active status (TRUE/FALSE)
- **is_featured**: Featured status (TRUE/FALSE)

### Vehicle Compatibility
- **vehicle_variants**: Comma-separated list of compatible vehicle variants
  - Format: "Toyota Camry 2020,Honda Civic 2021,BMW X3 2019"
  - Each variant should match existing vehicle variants in the system

## Data Format Guidelines

### Text Fields
- Use UTF-8 encoding for Arabic text
- Avoid special characters that might break CSV parsing
- Keep within specified character limits

### Numeric Fields
- Use decimal point (.) for decimal numbers
- Do not use thousand separators (commas)
- Negative numbers should use minus sign (-)

### Boolean Fields
- Use TRUE/FALSE (case insensitive)
- Alternatively: 1/0, Yes/No, Y/N

### Date Fields
- Use ISO format: YYYY-MM-DD
- Example: 2025-12-31

### Vehicle Variants
- Use exact vehicle variant names as they appear in the system
- Separate multiple variants with commas
- Example: "Toyota Camry 2020,Toyota Corolla 2019"

## Validation Rules

### Business Rules
1. **parts_number** must be unique across all parts
2. **category_name** and **brand_name** must exist in the system
3. **price** must be greater than 0
4. **quantity** cannot be negative
5. **safety_stock** should be less than **quantity**
6. **reorder_point** should be greater than **safety_stock**

### Data Integrity
- All required fields must have values
- Numeric fields must contain valid numbers
- Boolean fields must be TRUE/FALSE
- Dates must be in correct format

## Error Handling

### Common Errors
1. **Missing Required Fields**: Ensure all required fields have values
2. **Invalid Category/Brand**: Category and brand must exist in system
3. **Duplicate Parts Number**: Each part must have unique parts_number
4. **Invalid Vehicle Variants**: Vehicle variants must match system records
5. **Invalid Data Types**: Ensure numeric fields contain numbers, booleans are TRUE/FALSE

### Error Reporting
- Import process will generate detailed error report
- Errors are reported per row with specific field information
- Fix errors and re-import only failed rows

## Best Practices

### Data Preparation
1. **Validate Data**: Check all data before import
2. **Test Import**: Start with small batch to test format
3. **Backup**: Always backup existing data before bulk import
4. **Incremental Import**: Import in batches for large datasets

### Performance Tips
1. **Batch Size**: Import 100-500 rows at a time for optimal performance
2. **Off-Peak Hours**: Schedule large imports during low-traffic periods
3. **Monitor Progress**: Use import progress indicators

### Data Quality
1. **Consistent Naming**: Use consistent naming conventions
2. **Complete Information**: Provide as much detail as possible
3. **Regular Updates**: Keep data current and accurate
4. **Validation**: Validate critical fields like pricing and inventory

## Example Usage

### Sample CSV Row
```csv
VP001,Brake Pad Set Front,طقم فرامل أمامي,EA,2.500,2.200,"150x100x20mm",BP-FRONT-001,OEM-BP-001,FERT,1000,A001,WH01,BIN-A1,BRAKE,AUTO,1,OLD-BP-001,2025-12-31,EXT-BRAKE,A,50,10,25,7,2,PD,MRP1,C001,3000,1,125.50,150.00,S,Brake Components,Toyota,175.00,100,https://example.com/brake-pad.jpg,24,TRUE,FALSE,125.50,20,"Toyota Camry 2020,Toyota Corolla 2019",A001
```

### Import Process
1. Download the CSV template
2. Fill in your part data following the guidelines
3. Validate data format and completeness
4. Upload CSV file through vendor portal
5. Review import results and fix any errors
6. Verify imported parts in the system

## Support
For technical support or questions about the import process, contact the system administrator or refer to the vendor portal help section.