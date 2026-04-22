from db_manager import create_db, add_customer, add_company, add_product

create_db()
cust_id = add_customer("Apex Nutrition")

huel_id = add_company(cust_id, "Huel", "https://huel.com/")
tl_id = add_company(cust_id, "Transparent Labs", "https://www.transparentlabs.com/")
ghost_id = add_company(cust_id, "Ghost Lifestyle", "https://www.ghostlifestyle.com/")

add_product(huel_id, "Huel Protein Powder", "https://huel.com/products/huel")
add_product(huel_id, "Huel Pre-Workout", "https://huel.com/products/huel-energy-plus")
add_product(huel_id, "Huel Shaker Bottle", "https://huel.com/products/new-huel-shaker")

add_product(tl_id, "Transparent Labs Pre-Workout", "https://www.transparentlabs.com/products/lean-preworkout?selling_plan=1706524765&variant=39291537096797")
add_product(tl_id, "Transparent Labs Protein Bars", "https://www.transparentlabs.com/products/protein-bars?variant=41176385060957&selling_plan=1706524765")
add_product(tl_id, "Transparent Labs Protein Powder", "https://www.transparentlabs.com/products/whey-protein-isolate?variant=39366090752093&selling_plan=1706524765")

add_product(ghost_id, "Ghost Pre-Workout", "https://www.ghostlifestyle.com/products/ghost-legend-v4-x-sour-strips-rainbow")
add_product(ghost_id, "Ghost Protein Powder", "https://www.ghostlifestyle.com/products/ghost-whey-x-cocoa-puffs-cocoa-puffs-cereal-milk")
add_product(ghost_id, "Ghost Shaker Bottle", "https://www.ghostlifestyle.com/products/ghost-logo-shaker-infrared")






