import os
import numpy as np
import scipy.io as io

#----------------------------------------------------------------------
# The following script loads the S&P 500 and Fama-French data
# for the Stat240 final project, matches them by date, and
# calculates returns from the asset prices. 

# function to convert prices to returns
def prices_to_returns(p):
    """
    Convert prices to returns.
    """
    p = np.asarray(p)
    p = p.astype(float)
    m = len(p)
    r = np.zeros((m-1,1))
    for i in xrange(m-1):
        r[i] = (p[i+1]-p[i])/p[i]
    return r

# function to load csv and txt data
def load_text(csvfile, sep=",", num_headerlines=0, header_return=None):
    """
    Load data from text files, skipping num_headerlines and returning the 
    header_return line as a separate output.
    """
    loaded_csv = open(csvfile, 'r')
    out = []
    for row in loaded_csv:
        if sep is not None:
            out.append(row.strip().split(sep))
        else:
            out.append(row.strip().split())
    if header_return is not None:
        header = out[header_return]
    else:
        header = False
    out = out[num_headerlines:] # strip header
    return header, out

def get_dates_yahoo(yahoo_list,order="chronological"):
    """
    Get data information from yahoo finance data,
    removing the hyphens and tabs. Order specifies 
    whether the data and returns are given in chronological
    or reverse order.
    """
    list_of_lists = [item[0].split("\t") for item in yahoo_list]
    dates = [item[0] for item in list_of_lists]
    returns = [item[4] for item in list_of_lists]
    yahoo_dates = []
    for yd in dates:
        yd_all = yd.split('-')
        whole = ''
        for part in yd_all:
            whole += part
        yahoo_dates.append(whole[1:9])
    if order == "chronological":
        yahoo_dates = yahoo_dates[::-1]
        yahoo_returns = returns[::-1]
        return yahoo_dates, yahoo_returns
    elif order == "reverse":
        return yahoo_dates, yahoo_returns
    else:
        raise ValueError("'order' value is incorrect")

def match_data(daily_dates, daily_returns, target_dates):
    """
    Given a set of target dates and a set of daily dates (from returns), 
    construct a set of dates from the daily data that best match the 
    target dates. If no date in daily_dates can be found to match a 
    target date, replace it with the closest previous date. Record and 
    return how many of the days are inexact in 'misses', and return 
    the date matched daily returns. 
    """
    # Get indices of daily Libor returns that appear in Fama-French data
    daily_indices = [idx for idx, dd in zip(range(len(daily_dates)), daily_dates) if dd in target_dates]
    daily_matched_returns = np.zeros(len(daily_indices),)
    daily_matched_dates = np.array(daily_dates)[daily_indices]
    matches = [item for item in daily_matched_dates if item in target_dates]
    misses = [item for item in target_dates if item not in matches]

    # Find and replace missing dates with the previous date's data
    j = 0
    daily_matched_dates = daily_matched_returns.copy()
    for i in xrange(len(target_dates)):
        if target_dates[i] not in misses:
            daily_matched_returns[i] = daily_returns[daily_indices[j]]
            daily_matched_dates[i] = daily_dates[daily_indices[j]]
            j += 1
        else:
            daily_matched_returns[i] = daily_returns[daily_indices[j]]
            daily_matched_dates[i] = daily_dates[daily_indices[j]]
    return misses, daily_matched_dates, daily_matched_returns

def match_dates_and_save(input_list, target_path, order="chronological", 
                         save_mat=True, input_sep=",", target_sep=None, risk_free_path=None): 
    """
    Main parsing function. Combines other functions in this file to load data, 
    match daily price dates to target dates, convert to returns, and save the data. 

    It iterates over a list of input files, and can output a .MAT file whose columns are
    the matched returns for the inputs in the list.

    If output_type is "premiums", the path to a risk free asset must be specifed in 
    risk_free_path. This should be of the same format as the input file, but already
    matched to the target.
    """
    # make sure input list is a list
    if type(input_list) != type([]):
        input_list = [input_list]

    # initialize containers
    if save_mat:
        out_mat = None

    # load the target data -- NOTE: headers are particular to Fama-French data!
    print "\t--> Loading target data..."
    target_header, target_data = load_text(target_path, sep=target_sep, num_headerlines=3, header_return=1)

    # Convert target data to premiums, loading and subtracting risk_free asset
    if risk_free_path is not None:
        RF_header, RF_data = load_text(risk_free_path, sep=input_sep, num_headerlines=0, header_return=None) 
        target_indices = [1,4,7,10,13,16]
        target_data_out = (np.array(target_data).astype(float) - (1./(12*100.))*np.asarray(RF_data).astype(float))[:,target_indices]

    # loop over input paths
    for input_tuple in input_list:
        # get path and output type
        input_path = input_tuple[0]
        output_type = input_tuple[1]

        # load the input data, assuming standard Yahoo! Finance header
        input_header, input_data = load_text(input_path, sep=input_sep, num_headerlines=1, header_return=0) 
        print "Matching data from", input_path

        # Get dates for input
        print "\t--> Getting dates..."
        input_dates, input_data = get_dates_yahoo(input_data)

        # Get target dates
        target_dates = [td[0] for td in target_data]

        # Set output type
        if output_type is "returns" or "premiums":
            print "\t--> Converting", input_path, "to returns."
            input_data = prices_to_returns(input_data)
        else:
            print "\t--> Returning prices for", input_path

        # Match input to target dates and get matched returns
        print "\t--> Matching to target..."
        missed_target_dates, matched_input_dates, matched_input_data = match_data(input_dates, input_data, target_dates)
        if missed_target_dates != []:
            print "\t--> Number of missed target dates in", target_path, "by", input_path, ":", missed_target_dates
            print "\t--> Replacing with data from closest previous date."
            
        # If output_type is premiums, convert to premiums using matched Libor data
        if output_type=="premiums" and risk_free_path is not None:
            print "\t--> Converting", input_path, "to premiums."

            # load and subtract risk_free asset
            matched_input_data = matched_input_data - (1./(12*100.))*np.squeeze(np.asarray(RF_data).astype(float))

        # Save matched returns
        outpath = os.path.join(os.path.abspath('.'),output_type)
        outfile = os.path.join(outpath,input_path.split('/')[-1].split('.')[0]+'_returns.csv') # danger, input path should have just one '.'
        print "\t--> Saving matched data as", outfile
        np.savetxt(outfile, matched_input_data, delimiter=",")

        if save_mat:
            if out_mat is None:
                out_mat = np.array(matched_input_data)
            else:
                out_mat = np.vstack((out_mat, np.array(matched_input_data)))

    if save_mat:
        mat_outpath = os.path.join(os.path.abspath('.'),'matfiles/')
        out_dict = {'predictors':out_mat.T, 'targets':target_data_out}
        io.savemat(mat_outpath+'All_variables_matched.mat', out_dict)

if __name__ == '__main__':
    input_list = [('./raw/GoldSilver.csv','returns'),('./raw/Nasdaq.csv','returns'), ('./raw/NYSE_Composite.csv','returns'), ('./raw/Treasury10yr.csv','prices'), ('./raw/Treasury_5year.csv','prices'), ('./raw/VIX.csv','returns'), ('./raw/SP500_Revised.csv','premiums')]
    target_path = './raw/FF6Portfolios.txt'
    match_dates_and_save(input_list, target_path, order="chronological", 
                         save_mat=True, input_sep=",", target_sep=None, 
                         risk_free_path='./returns/Libor_returns.csv')


