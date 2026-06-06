import pandas as pd
import datetime

def create_sample_file():
    # Products lookup table
    products_data = {
        "ProductID": ["P001", "P002", "P003", "P004", "P005"],
        "ProductName": ["AeroBook Laptop", "Spectre Wireless Mouse", "Apex Keyboard", "Nexus Type-C Hub", "Titan 4K Monitor"],
        "Category": ["Computers", "Accessories", "Accessories", "Accessories", "Displays"],
        "UnitCost": [750.00, 12.50, 42.00, 18.00, 220.00]
    }
    df_products = pd.DataFrame(products_data)

    # Sales transaction table
    sales_data = {
        "OrderID": ["10001", "10002", "10003", "10004", "10005", "10006", "10007", "10008"],
        "OrderDate": [
            datetime.date(2026, 5, 10),
            datetime.date(2026, 5, 11),
            datetime.date(2026, 5, 11),
            datetime.date(2026, 5, 12),
            datetime.date(2026, 5, 13),
            datetime.date(2026, 5, 13),
            datetime.date(2026, 5, 14),
            datetime.date(2026, 5, 15)
        ],
        "CustomerID": ["C_902", "C_904", "C_902", "C_905", "C_904", "C_901", "C_903", "C_905"],
        "ProductID": ["P001", "P002", "P001", "P003", "P005", "P004", "P005", "P002"],
        "UnitPrice": [1100.00, 25.00, 1100.00, 75.00, 350.00, 35.00, 350.00, 25.00],
        "Quantity": [1, 2, 1, 1, 2, 4, 1, 10],
        "SalesAmount": [1100.00, 50.00, 1100.00, 75.00, 700.00, 140.00, 350.00, 250.00]
    }
    df_sales = pd.DataFrame(sales_data)

    # Write to an Excel workbook with multiple tabs
    output_filename = "sample_sales.xlsx"
    with pd.ExcelWriter(output_filename, engine="openpyxl") as writer:
        df_sales.to_excel(writer, sheet_name="Sales", index=False)
        df_products.to_excel(writer, sheet_name="Products", index=False)

    print(f"Sample Excel sheet generated: {output_filename}")

if __name__ == "__main__":
    create_sample_file()
