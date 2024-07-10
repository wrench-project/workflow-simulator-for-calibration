#!/usr/bin/env python3

import os
import sys
import json
import math
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def create_colors_and_line_styles(num_series):
    colors = ['red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow']
    line_styles = ['-', '--']  # Solid line and dashed line

    # Repeat colors and line styles to cover all series
    colors = (colors * (num_series // 2))[:num_series]
    line_styles = (line_styles * (num_series // 2))[:num_series]

    return colors, line_styles

# Calculates the number of bins using the square root rule.
def sqrt_rule_bins(data):
    n = len(data)
    num_bins = int(math.sqrt(n))
    return num_bins

# Calculates the number of bins using Sturges' Rule.
def sturges_rule_bins(data):
    n = len(data)
    num_bins = int(1 + math.log2(n))
    return num_bins

# Calculates the number of bins using the Freedman-Diaconis Rule.
def freedman_diaconis_bins(data):
    iqr = np.percentile(data, 75) - np.percentile(data, 25)
    n = len(data)
    bin_width = (2 * iqr) / (n ** (1/3))
    data_range = max(data) - min(data)
    num_bins = int(data_range / bin_width)
    return num_bins

# Plots a density plot
def density_plot(data_list, labels, colors, line_styles, filename, bins, cumulative):
    plt.figure(figsize=(8, 6))  # Set the figure size
    
    # Create the histogram as a line plot
    #plt.hist(data, density=True, histtype='step', bins=bins, cumulative=cumulative, color='blue')
    

    # Iterate over the data list and create density plots
    for i, data in enumerate(data_list):
        plt.hist(data, density=True, histtype='step', bins=bins, cumulative=cumulative, label=labels[i], color=colors[i], linestyle=line_styles[i])


    # Add labels and title
    plt.xlabel('Values')
    plt.ylabel('Density')
    plt.title('Histogram Density Plot (RS - BO)')

    # # Show the y-axis at x = 0
    # plt.axvline(0, color='black', lw=1)

    # Add gridlines
    plt.grid(True)

    plt.legend()  # Show legend for the data series

    plt.savefig(filename, format='pdf')  # Save plot as PDF
    plt.close()  # Close the figure to release memory


def probability_density_plot(data_list, labels, colors, line_styles, filename):
    sns.set_style('whitegrid')  # Set the plot style

    # Create the density plot using seaborn
    for i, data in enumerate(data_list):
        sns.kdeplot(data, label=labels[i], color=colors[i], linestyle=line_styles[i], fill=False)

    # Set the plot labels and title
    plt.xlabel('Values')
    plt.ylabel('Probability Density Function')
    plt.title('Probability Density Plot (RS - BO)')

    # Display the legend
    plt.legend()

    plt.savefig(filename, format='pdf')  # Save plot as PDF
    plt.close()  # Close the figure to release memory

def box_plot(data_list, labels, filename):
    plt.figure(figsize=(8, 6))  # Set the figure size
    
    # Create the box plot
    plt.boxplot(data_list, labels=labels)

    # Add labels and title
    plt.xlabel('Data Series')
    plt.ylabel('Values')
    plt.title('Box Plot (RS - BO)')

    plt.savefig(filename, format='pdf')  # Save plot as PDF
    plt.close()  # Close the figure to release memory

def violin_plot(data_list, labels, filename):
    plt.figure(figsize=(8, 6))  # Set the figure size
    
    # Create the violin plot
    plt.violinplot(data_list)

    # Add labels and title
    plt.xlabel('Data Series')
    plt.ylabel('Values')
    plt.title('Violin Plot (RS - BO)')

    # Customize x-axis tick labels
    x_ticks = range(1, len(data_list) + 1)
    plt.xticks(x_ticks, labels)

    plt.savefig(filename, format='pdf')  # Save plot as PDF
    plt.close()  # Close the figure to release memory

def cumulative_plot(data_list, labels, colors, line_styles, filename):
    plt.figure(figsize=(8, 6))  # Set the figure size

    for i, data in enumerate(data_list):
        # Sort the data in ascending order
        sorted_data = np.sort(data)

        # Compute the cumulative probabilities
        cumulative_probs = np.arange(1, len(sorted_data) + 1) / len(sorted_data)

        # Plot the cumulative distribution
        plt.plot(sorted_data, cumulative_probs, label=labels[i], color=colors[i], linestyle=line_styles[i])

    # Add labels, title, and legend
    plt.xlabel('Values')
    plt.ylabel('Cumulative Probability')
    plt.title('Cumulative Distribution Plot')
    plt.legend()

    plt.savefig(filename, format='pdf')  # Save plot as PDF
    plt.close()  # Close the figure to release memory

def process_json_files(file_paths):
    data = list()

    for file_path in file_paths:
        with open(file_path, 'r') as file:
            try:
                run_dict = json.load(file)

                # Process the JSON data here
                print(f"Processing {file_path}...")
                # print(json_data)
                # print()

                temp_data = list()
                count_err = 0
                for exp in run_dict["experiments"]:
                    for sim in exp["simulate"]:
                        try:
                            rs = float(sim["rs"].split(":")[2])
                            bo = float(sim["bo"].split(":")[2])
                            temp_data.append(rs - bo)
                        except ValueError:
                            count_err += 1
                temp_data.sort()
                if count_err > 0:
                    print(f"{count_err} simulations did not complete")

                print(len(temp_data))

                data.append(temp_data)

            except json.JSONDecodeError as e:
                print(f"Error processing {file_path}: {e}")

    return data

def main():
    # Get the command-line arguments excluding the script name
    prefix = sys.argv[1]
    file_paths = sys.argv[2:]

    # Check if any file paths were provided
    if len(file_paths) == 0:
        print("No file paths provided.")
        sys.exit(1)


    
    data   = process_json_files(file_paths)

    labels = []
    colors = []
    line_styles = []

    if len(data) == 4:
        labels = ['30s', '60s', '120s', '300s']
        colors = ['red', 'blue', 'green', 'orange']
        line_styles = ['-', '-', '-', '-']
    elif len(data) == 8:
        labels = ['s_30s', 's_60s', 's_120s', 's_300s', 'c_30s', 'c_60s', 'c_120s', 'c_300s']
        colors = ['red', 'blue', 'green', 'orange', 'red', 'blue', 'green', 'orange']
        line_styles = ['-', '-', '-', '-', '--', '--', '--', '--']
    elif len(data) == 2:
        labels = ['simple', 'complex']
        colors = ['red', 'blue']
        line_styles = ['-', '-']

    # density_plot(data, labels)
    # continuous_density_plot(data, labels)

    bins = freedman_diaconis_bins(data[0])
    #density_plot(data, labels, colors, line_styles, prefix + '_density.pdf', bins, False)
    #density_plot(data, labels, 'test_continuous_density.pdf', bins, True)

    probability_density_plot(data, labels, colors, line_styles, prefix + '_prob_density.pdf')

    box_plot(data, labels, prefix + '_box.pdf')
    violin_plot(data, labels, prefix + '_violin.pdf')
    cumulative_plot(data, labels, colors, line_styles, prefix + '_cumulative.pdf')

if __name__ == "__main__":
    main()


# # Example usage
# data_list = [
#     [1.2, 1.5, 1.7, 2.0, 2.5, 2.7, 3.1, 3.5, 3.8, 4.2, 4.5],
#     [2.1, 2.4, 2.7, 3.0, 3.2, 3.5, 3.8, 4.1, 4.4, 4.7, 5.0],
#     [3.5, 2.4, 2.1, -3.0, 3.2, 3.5, 3.8, 4.1, 4.4, 4.7, 6.0]
# ]
# labels = ['Series 1', 'Series 2', 'Series 3']

# create_density_plot(data_list, labels)
