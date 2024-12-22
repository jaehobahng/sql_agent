-- Create the product_info table
CREATE TABLE product_info (
    product_id INT PRIMARY KEY,
    product_category VARCHAR(50),
    product_name VARCHAR(100),
    brand_name VARCHAR(50),
    original_price DECIMAL(10, 2),
    current_price DECIMAL(10, 2)
);

-- Create the purchase_info table
CREATE TABLE purchase_info (
    purchase_id INT PRIMARY KEY,
    date DATE,
    user_id INT,
    product_id INT,
    purchase_qty INT,
    purchase_amt_original DECIMAL(10, 2),
    purchase_amt_actual DECIMAL(10, 2),
    product_actual_price DECIMAL(10, 2),
    product_original_price DECIMAL(10, 2),
    FOREIGN KEY (product_id) REFERENCES product_info(product_id)
);
