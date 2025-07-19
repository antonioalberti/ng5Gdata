import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# Read the CSV data from the file 'data.csv'
# The CSV file is expected to be in the same directory as the script.
# We need to skip the first row which contains the system names, and use the second row as header.
# Also, the 'Data Transfer Rate (KB/s)' columns have commas, which need to be removed.
# Explicitly read the relevant columns as strings to avoid issues with .str accessor.
df = pd.read_csv('data.csv', header=1, dtype={'Data Transfer Rate (KB/s)': str})

# Clean column names and data
# Corrected the column assignment to include the 5th column which was previously missed.
df.columns = ['Image', 'Size_Bytes_CDN', 'Data_Transfer_Rate_KB_s_CDN', 'Transfer_Time_s_CDN', '_empty_col_', 'Image_NG', 'Size_Bytes_NG', 'Data_Transfer_Rate_KB_s_NG', 'Transfer_Time_s_NG']

# Select relevant columns and clean them
# Ensure data is numeric, coercing errors to NaN and then filling them if necessary (though not expected here)
cdn_rate = pd.to_numeric(df['Data_Transfer_Rate_KB_s_CDN'].str.replace(',', ''), errors='coerce') / (1024 * 1024)
ng_rate = pd.to_numeric(df['Data_Transfer_Rate_KB_s_NG'].str.replace(',', ''), errors='coerce') / (1024 * 1024)
image_numbers = df['Image']

# Drop rows where rates might be NaN after coercion, if any
df_cleaned = df.dropna(subset=['Data_Transfer_Rate_KB_s_CDN', 'Data_Transfer_Rate_KB_s_NG'])
cdn_rate = pd.to_numeric(df_cleaned['Data_Transfer_Rate_KB_s_CDN'].str.replace(',', ''), errors='coerce') / (1024 * 1024)
ng_rate = pd.to_numeric(df_cleaned['Data_Transfer_Rate_KB_s_NG'].str.replace(',', ''), errors='coerce') / (1024 * 1024)
image_numbers = df_cleaned['Image']


# Calculate cumulative average and standard deviation
# Use .expanding() for cumulative calculations
cdn_cumulative_avg = cdn_rate.expanding().mean()
cdn_cumulative_std = cdn_rate.expanding().std()
# Handle potential NaN for std dev on the first element
cdn_cumulative_std = cdn_cumulative_std.fillna(0) 
cdn_upper_error = cdn_cumulative_avg + cdn_cumulative_std
cdn_lower_error = cdn_cumulative_avg - cdn_cumulative_std

ng_cumulative_avg = ng_rate.expanding().mean()
ng_cumulative_std = ng_rate.expanding().std()
# Handle potential NaN for std dev on the first element
ng_cumulative_std = ng_cumulative_std.fillna(0)
ng_upper_error = ng_cumulative_avg + ng_cumulative_std
ng_lower_error = ng_cumulative_avg - ng_cumulative_std

# Create subsampled indices (every 10th point)
subsample_factor = 5
subsample_indices = np.arange(0, len(image_numbers), subsample_factor)

# Create transfer rate plot
plt.figure(figsize=(16, 7))

# Plot cumulative average with error bars for CDN (subsampled)
plt.errorbar(image_numbers[subsample_indices], cdn_cumulative_avg[subsample_indices], 
             yerr=[(cdn_cumulative_avg - cdn_lower_error)[subsample_indices], 
                   (cdn_upper_error - cdn_cumulative_avg)[subsample_indices]],
             fmt='-o', color='blue', ecolor='lightblue',
             capsize=3, markersize=4, elinewidth=1,
             label='Baseline - Traditional CDN (Cumulative Avg)')

# Plot cumulative average with error bars for NovaGenesis (subsampled)
plt.errorbar(image_numbers[subsample_indices], ng_cumulative_avg[subsample_indices],
             yerr=[(ng_cumulative_avg - ng_lower_error)[subsample_indices], 
                   (ng_upper_error - ng_cumulative_avg)[subsample_indices]],
             fmt='-o', color='green', ecolor='lightgreen',
             capsize=3, markersize=4, elinewidth=1,
             label='NovaGenesis - Named Content Distribution (Cumulative Avg)')

# Add instantaneous values plots with light colors (subsampled)
plt.scatter(image_numbers[subsample_indices], cdn_rate[subsample_indices], 
            label='Baseline - Traditional CDN (Instantaneous)', color='skyblue', alpha=0.6, s=10)
plt.scatter(image_numbers[subsample_indices], ng_rate[subsample_indices], 
            label='NovaGenesis - Named Content Distribution (Instantaneous)', color='lightgreen', alpha=0.6, s=10)

# Add labels and title
plt.xlabel('.JPG file', fontsize=14) 
plt.ylabel('Data Transfer Rate (MB/s)', fontsize=14)
plt.legend(fontsize=14)
plt.grid(True)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)
plt.ylim(0.0094, 0.0115)
plt.tight_layout()
plt.savefig('data_transfer_rate_plot.pdf')

# Create delay plot (using transfer time as delay)
plt.figure(figsize=(16, 7))

# Get transfer time data
cdn_time = pd.to_numeric(df_cleaned['Transfer_Time_s_CDN'], errors='coerce')
ng_time = pd.to_numeric(df_cleaned['Transfer_Time_s_NG'], errors='coerce')

# Calculate cumulative stats for delay
cdn_time_avg = cdn_time.expanding().mean()
cdn_time_std = cdn_time.expanding().std().fillna(0)
cdn_time_upper = cdn_time_avg + cdn_time_std
cdn_time_lower = cdn_time_avg - cdn_time_std

ng_time_avg = ng_time.expanding().mean()
ng_time_std = ng_time.expanding().std().fillna(0)
ng_time_upper = ng_time_avg + ng_time_std
ng_time_lower = ng_time_avg - ng_time_std

# Plot delay with error bars
plt.errorbar(image_numbers[subsample_indices], cdn_time_avg[subsample_indices],
             yerr=[(cdn_time_avg - cdn_time_lower)[subsample_indices],
                   (cdn_time_upper - cdn_time_avg)[subsample_indices]],
             fmt='-o', color='blue', ecolor='lightblue',
             capsize=3, markersize=4, elinewidth=1,
             label='Baseline - Traditional CDN (Cumulative Avg)')

plt.errorbar(image_numbers[subsample_indices], ng_time_avg[subsample_indices],
             yerr=[(ng_time_avg - ng_time_lower)[subsample_indices],
                   (ng_time_upper - ng_time_avg)[subsample_indices]],
             fmt='-o', color='green', ecolor='lightgreen',
             capsize=3, markersize=4, elinewidth=1,
             label='NovaGenesis - Named Content Distribution (Cumulative Avg)')

# Add instantaneous values
plt.scatter(image_numbers[subsample_indices], cdn_time[subsample_indices],
            label='Baseline - Traditional CDN (Instantaneous)', color='skyblue', alpha=0.6, s=10)
plt.scatter(image_numbers[subsample_indices], ng_time[subsample_indices],
            label='NovaGenesis - Named Content Distribution (Instantaneous)', color='lightgreen', alpha=0.6, s=10)

plt.xlabel('.JPG file', fontsize=14)
plt.ylabel('Transfer time (s)', fontsize=14)
plt.legend(fontsize=14)
plt.grid(True)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)
plt.tight_layout()
plt.savefig('delay_plot.pdf')

print("Python code to generate both plots has been prepared.")
# The code itself is the result.
