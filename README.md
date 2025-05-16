# Scraper

This project scrapes Reddit posts using the URS Reddit scraping library (https://github.com/JosephLai241/URS) and processes the results for clustering and content analysis.

## Setup

1. Clone this repository:

    git clone https://github.com/Aronart/Scraper.git
    cd Scraper

2. Set your OPENAI_API_KEY in Scraper/.env:

3. Clone the URS repository:

    git clone --depth=1 https://github.com/JosephLai241/URS.git

Note: URS's own guide recommends the following setup:

    cd URS
    poetry install
    poetry shell
    maturin develop --release

However, this project calls URS via subprocess using a configured Python environment and doesn't require those steps unless you're running URS directly. In this setup, URS is invoked like this:

    command = [
        str(URS_VENV_PYTHON), '-m', 'urs.Urs',
        '-r', subreddit,
        's', keyword
    ]
    subprocess.run(
        command,
        cwd=URS_PATH,
        input='y\n',
        text=True
    )

4. Set up Reddit API credentials:

Create a `.env` file inside `Scraper/URS/` with your Reddit API credentials. See:
https://josephlai241.github.io/URS/credentials.html

5. Install the required Python packages:

    cd Scraper
    pip install -r requirements.txt

## Usage

Step 1 – Scrape Reddit data:

    python scraper.py reddit --subreddits arbeitsleben dejobs --keywords Quereinstieg IT-Beratung

Step 2 – Export scraped data to CSV:

    python export_all_to_csv.py

Step 3 – Cluster the data:

    python cluster.py

Step 4 – Generate content based on clusters:

    python content.py

## Output

This pipeline produces:
- Raw and cleaned Reddit data
- Clustered results
- Final summarized content

## Notes

- URS must be cloned and available in `Scraper/URS/`
- This project uses subprocess calls to run URS commands programmatically
