# Amazon PA-API Integration

This repository includes a GitHub Actions workflow that automatically enhances Amazon affiliate links in blog posts using Amazon Product Advertising API (PA-API).

## Features

- Automatically detects Amazon links in markdown files
- Fetches product information (title, image) from Amazon PA-API
- Replaces simple links with rich product cards
- Maintains affiliate tags
- Runs automatically on push or can be triggered manually

## Setup

### 1. Get Amazon PA-API Credentials

1. Sign up for Amazon Associates program: https://affiliate.amazon.co.jp/
2. Register for Product Advertising API: https://affiliate.amazon.co.jp/assoc_credentials/home
3. Get your Access Key and Secret Key

### 2. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

- `AMAZON_ACCESS_KEY`: Your PA-API Access Key
- `AMAZON_SECRET_KEY`: Your PA-API Secret Key
- `AMAZON_PARTNER_TAG`: Your Amazon Associate Tag (default: peipeipe-22)

To add secrets:
1. Go to your repository Settings
2. Navigate to Secrets and variables > Actions
3. Click "New repository secret"
4. Add each secret with its value

### 3. Usage

The workflow runs automatically when:
- You push changes to markdown files in `_posts/` directory
- You manually trigger it from Actions tab

#### Supported Link Formats

The script recognizes these Amazon link formats:

```markdown
[Product Name](https://www.amazon.co.jp/dp/B084MCR9KG)
[Product Name](http://www.amazon.co.jp/exec/obidos/ASIN/4062737388/peipeipe-22/ref=nosim/)
[Product Name](https://amzn.to/3VFbQSJ)
```

#### Output Format

Links are replaced with rich product cards:

```html
<div class="amazon-product-card" style="...">
  <div class="amazon-product-image">
    <a href="..."><img src="..." alt="Product Title"></a>
  </div>
  <div class="amazon-product-info">
    <h3><a href="...">Product Title</a></h3>
    <div class="amazon-product-link">
      <a href="...">Amazon.co.jpで詳細を見る</a>
    </div>
  </div>
</div>
```

### 4. Manual Run

To manually enhance Amazon links in your local environment:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AMAZON_ACCESS_KEY="your-access-key"
export AMAZON_SECRET_KEY="your-secret-key"
export AMAZON_PARTNER_TAG="peipeipe-22"

# Run the script
python scripts/enhance_amazon_links.py
```

## Notes

- Already enhanced links are automatically skipped
- The script only processes the first occurrence of each product per file
- Short URLs (amzn.to) are resolved to extract product ASINs
- Invalid or unavailable products are skipped with a warning

## Troubleshooting

### API Rate Limits

Amazon PA-API has rate limits. If you hit the limit:
- The script will skip products it cannot fetch
- Run the workflow again later for remaining products

### Missing Credentials

If credentials are not configured, the workflow will fail with:
```
Error: AMAZON_ACCESS_KEY and AMAZON_SECRET_KEY environment variables must be set
```

Make sure all three secrets are configured in GitHub repository settings.

### Product Not Found

If a product cannot be found:
- The ASIN might be invalid or unavailable
- The product might be region-specific
- Check the error messages in the workflow logs

## Related Files

- `.github/workflows/enhance-amazon-links.yml` - GitHub Actions workflow
- `scripts/enhance_amazon_links.py` - Python script for processing
- `requirements.txt` - Python dependencies
