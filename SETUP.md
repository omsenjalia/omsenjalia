# Setup (about 5 minutes)

1. On GitHub, create a NEW PUBLIC repository named exactly `omsenjalia`
   (same as your username). Tick "Add a README" is NOT needed.
2. Put every file from this folder into that repository, keeping the folders:
   - README.md
   - generate.py
   - assets/            (starter images, replaced automatically)
   - .github/workflows/update.yml
3. In the repository open Settings > Actions > General > Workflow permissions
   and choose "Read and write permissions", then Save.
4. Open the Actions tab, pick "Update profile README", press "Run workflow".
5. After ~30 seconds your profile page shows the live version.
   It then refreshes itself every 6 hours.

## Changing things
- Weather location: WEATHER_LAT / WEATHER_LON in .github/workflows/update.yml
- Number of pinned / random cards: NUM_PINNED / NUM_RANDOM at the top of generate.py
- Pinned projects come from the repos you pin on your GitHub profile.
- Random picks are 2 other repos chosen at random on every refresh.
