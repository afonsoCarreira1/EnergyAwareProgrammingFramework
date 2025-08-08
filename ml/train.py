import numpy as np 
import matplotlib.pyplot as plt 
import math
import pandas as pd 
import seaborn as sns
import os, subprocess
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor 
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score
from sklearn.tree import plot_tree
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from joblib import dump, load
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.colors import ListedColormap
from scipy.stats import pearsonr, spearmanr
import shutil
import re
from pysr import PySRRegressor
from m3gp.M3GP import M3GP

def print_full_df(df):
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
        print(df)

def clean_data(df,clean_zeros = True):
    df = drop_column(df,'Filename')
    col_name = 'EnergyUsed'
    df = df.replace([np.inf, -np.inf], np.nan)  # Replace infinity with NaN
    if clean_zeros: df[col_name] = df[col_name].replace(0.0, np.nan)
    df = df.dropna(subset=[col_name])
    return df

def separate_data(df,collection):
    if collection == 'ArrayList': return df[
        df['Filename'].str.contains(collection, case=False, na=False) & 
        ~df['Filename'].str.contains('CopyOnWriteArrayList', case=False, na=False)]
    return df[df['Filename'].str.contains(collection, case=False, na=False)]

def drop_column(df,column_name):
    if column_name in df.columns:df = df.drop(columns=[column_name])
    else: print(f"Column '{column_name}' not found in DataFrame.")
    return df  

def get_scores(regressor,X_test,y_test,log):
    # Evaluate the model
    predictions = regressor.predict(X_test)
    mse = mean_squared_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    log.append(f"Mean Squared Error: {mse}")#mse:.4f
    log.append(f"R² Score: {r2:.4f}")

def save_figure_pdf(df, regressor):
    plt.figure(figsize=(25, 15))  # Increase size for better visibility
    plot_tree(
        regressor, 
        feature_names=df.columns[:-1],  # Column names for clarity
        filled=True, 
        rounded=True, 
        precision=2
    )
    plt.title('Decision Tree Visualization')

    # Save plot to PDF with higher resolution
    plt.savefig('ml/decision_tree_visualization.svg', format='svg', bbox_inches='tight', dpi=300)
    plt.close()  # Close the plot to avoid displaying it inline

def comparison(y,y_pred):
    comparison_df = pd.DataFrame({
    'Real Energy': y[:20],
    'Predicted Energy': y_pred[:20],
    'Difference': y[:20] - y_pred[:20]
    })
    # Exibir a comparação
    print(comparison_df)

def plot_prediction_vs_feature2(model, X, y, column_name):
    """
    Plots predicted energy vs. a selected feature on a log scale, alongside real energy values.

    Parameters:
    - regressor: Trained DecisionTreeRegressor model
    - X: Feature dataset (DataFrame)
    - y: True energy values (Series)
    - column_name: The feature column to plot against predictions
    """
    if column_name not in X.columns:
        print(f"Column '{column_name}' not found in dataset!")
        return

    y_pred = model.predict(X)  # Predict using full feature set
    feature_values_input1 = set(X['input1'])
    print(f"input1 (Size of each List) - Unique Values: {feature_values_input1}")
    comparison(y,y_pred)
    plt.figure(figsize=(8, 6))
    X_log = np.log1p(X[column_name])
    plt.scatter(X_log, y, label="Real Energy", alpha=0.6, color="blue", marker="o")
    plt.scatter(X_log, y_pred, label="Predicted Energy", alpha=0.6, color="red", marker="x")
    plt.xlabel(f"log(1 + {column_name})")
    plt.ylabel("Energy")
    plt.xscale("log")  # Log scale for the X-axis
    plt.title(f"Log-Scaled Predicted vs Real Energy for {column_name}")
    plt.legend()
    plt.grid(False)
    plt.show()

def plot_energy_vs_feature(X, y, column_name,log = False):
    """
    Plots actual energy vs. a selected feature for all inputs,
    and predicted energy for unique inputs.
    """
    if column_name not in X.columns:
        print(f"Column '{column_name}' not found in dataset!")
        return
    X_unique = X.drop_duplicates()
    energy_predicts = get_energy_predictions(X_unique)

    plt.figure(figsize=(8, 6))

    plt.scatter(X[column_name], y, label="Actual Energy", alpha=0.6, color="blue", marker="o")

    plt.scatter(X_unique[column_name], energy_predicts, label="Predicted Energy", color="red", marker="x")# alpha=0.8,s=75, linewidths=2,

    if column_name != 'input0': plt.xlabel(column_name) 
    else: plt.xlabel("input")
    plt.ylabel("Energy")
    if log:
        plt.yscale('log')
        plt.ylim()
    plt.title("Actual vs. Predicted Energy")
    plt.legend()
    plt.grid(False)
    plt.show()

def get_energy_predictions(df):
    energy_predict_for_input = []
    unique_vals = {col: df[col].unique() for col in df.columns}
    unique_inputs = unique_vals['input0']
    for input in unique_inputs:
        energy_predict_for_input.append(get_model_expression(input))
    return energy_predict_for_input



def plot_energy_vs_feature4(X, y, column_name, list_type_filter=None):
    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)

    list_columns = {
        'java.util.ArrayList': 'red',
        'java.util.Vector': 'blue',
        'java.util.concurrent.CopyOnWriteArrayList': 'green',
        'java.util.LinkedList': 'orange'
    }

    plt.figure(figsize=(8, 6))

    # Use filter if specified, else plot all
    columns_to_plot = (
        {list_type_filter: list_columns.get(list_type_filter)}
        if list_type_filter
        else list_columns
    )

    for list_type, color in columns_to_plot.items():
        if list_type not in X.columns:
            print(f"Warning: column '{list_type}' not found.")
            continue
        mask = X[list_type] == 1
        print(f"{list_type}: {mask.sum()} rows selected")
        if mask.sum() == 0:
            continue
        plt.scatter(
            X.loc[mask, column_name],
            y.loc[mask],
            label=list_type.split('.')[-1],
            color=color,
            alpha=0.6,
            marker='o'
        )
    if column_name == 'input0':column_name = 'list size'
    plt.xlabel(column_name)
    plt.ylabel("Energy")
    title = f"Energy vs {column_name}"
    if list_type_filter:
        title += f" (Filtered: {list_type_filter.split('.')[-1]})"
    else:
        title += " (Colored by List Type)"
    plt.title(title)
    plt.legend()
    plt.grid(False)
    plt.show()



def plot_energy_vs_feature3(X, y, column_name, var_type_filter=None):
    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)

    # Map variable types (or their identifying keywords in column names) to colors
    var_type_colors = {
        'Long': 'red',
        'Double': 'blue',
        'Int': 'green',
        'Float': 'orange',
        'Boolean': 'purple',
        'String': 'brown'
        # Add more types/colors here as needed
    }

    # Find all columns in X that match any of these types (case insensitive)
    # We consider a column belongs to a type if the type string appears in its name (case-insensitive)
    filtered_columns = {}
    for vt, color in var_type_colors.items():
        matching_cols = [col for col in X.columns if vt.lower() in col.lower()]
        if matching_cols:
            # For simplicity, treat all matching columns as that type and pick the first matching column
            filtered_columns[vt] = {
                'color': color,
                'columns': matching_cols
            }

    if var_type_filter:
        # Validate filter
        if var_type_filter not in filtered_columns:
            print(f"Variable type '{var_type_filter}' not found in columns.")
            return
        filtered_columns = {var_type_filter: filtered_columns[var_type_filter]}

    plt.figure(figsize=(8, 6))

    for vt, info in filtered_columns.items():
        color = info['color']
        cols = info['columns']
        # For each type, combine all columns (OR their masks) to select rows where any var of that type is present
        mask = X[cols].any(axis=1)
        print(f"{vt}: {mask.sum()} rows selected (from columns {cols})")
        if mask.sum() == 0:
            continue
        plt.scatter(
            X.loc[mask, column_name],
            y.loc[mask],
            label=vt,
            color=color,
            alpha=0.6,
            marker='o'
        )

    if column_name == 'input0':
        xlabel = 'list size'
    else:
        xlabel = column_name

    plt.xlabel(xlabel)
    plt.ylabel("Energy")
    title = f"Energy vs {xlabel}"
    if var_type_filter:
        title += f" (Filtered: {var_type_filter})"
    else:
        title += " (Colored by Variable Type)"
    plt.title(title)
    plt.legend()
    plt.grid(False)
    plt.show()


def model(df,modelPath,log):
    # Separate features and target
    X = df.iloc[:, :-1]  # All columns except the last one
    y = df.iloc[:, -1]   # Energy column
    #y = y*10**6
    #print(y)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42) 

    # Initialize and train the DecisionTreeRegressor
    log.append('Starting training ...')
    log.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.append("\n\n\n")
    decision_tree_regressor(X,y,X_train, X_test, y_train, y_test,modelPath,log,save = True)
    log.append("\n\n\n")
    log.append('Random Forest')
    log.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    random_forest_regression(X,y,X_train, X_test, y_train, y_test,modelPath,log,save = True)
    log.append("\n\n\n")
    log.append('Gradient Boosting')
    log.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    gradient_boosting_regression(X,y,X_train, X_test, y_train, y_test,modelPath,log,save = True)
    log.append("\n\n\n")
    log.append('Linear Regression')
    log.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    linear_regression(X,y,X_train, X_test, y_train, y_test,modelPath,log,save = True)
    log.append("\n\n\n")
    log.append('Pysr')
    log.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    pysr(X,y,X_train, X_test, y_train, y_test,modelPath,log)
    #log.append("\n\n\n")
    #log.append('m3gp')
    #log.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    #m3gp_model(X,y,X_train, X_test, y_train, y_test,modelPath,log,save = True)
    #log.append("\n\n\n")

    #checkStrangeValuesOfBubbleSort()
    #save_figure_pdf(df,regressor)
    #plot_energy_vs_feature(X,y,'ImportsUsed')
    #plot_prediction_vs_feature(regressor, X_test, y_test, 'input2')
    #plot3D(X,y)
    
#def checkStrangeValuesOfBubbleSort():
#    filtered_df = df.loc[(df['input1'] > 2743)]#.loc[(df['input1'] >= 1e3) & (df['input1'] <= 1e4)  ]#& (df['EnergyUsed'] >= 50)
#    filtered_df = filtered_df.sort_values(by='EnergyUsed')
#    # Find columns where all values are the same
#    constant_columns = filtered_df.nunique() == 1
#    # Drop those columns
#    filtered_df_cleaned = filtered_df.loc[:, ~constant_columns]
#    save_df_to_csv(filtered_df_cleaned)

def save_df_to_csv(df, filename="output.csv"):
    df.to_csv(filename, index=False)
    print(f"DataFrame saved to {filename}")

def tune_hyperparameters(X,y,X_train, X_test, y_train, y_test, selected_model,log):
    log.append(f'Best model scores of {selected_model}')

    #faster
    param_grid = {
        'max_depth': [3, 5, 10, 15, None],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 5],
        'max_features': [None, 'sqrt', 'log2'],
    }

    #takes a lot of time
    #param_grid = {
    #'max_depth': [3, 5, 10, 15, None, 20, 30],
    #'min_samples_split': [2, 5, 10, 20, 50],
    #'min_samples_leaf': [1, 2, 5, 10],
    #'max_features': [None, 'sqrt', 'log2', 0.1, 0.3, 0.5, 0.7],
    #'criterion': ['squared_error', 'friedman_mse', 'absolute_error', 'poisson'],
    #'splitter': ['best', 'random'],
    #'max_leaf_nodes': [None, 10, 50, 100],
    #'min_impurity_decrease': [0.0, 0.01, 0.1],
    #'ccp_alpha': [0.0, 0.01, 0.1]
    #}


    models = {
    "decision_tree_regressor": DecisionTreeRegressor(random_state=42),
    "random_forest": RandomForestRegressor(random_state=42),
    "gradient_boosting": GradientBoostingRegressor(random_state=42),
    }

    grid_search = GridSearchCV(estimator=models[selected_model],
                               param_grid=param_grid, 
                               cv=5,
                               scoring='neg_mean_squared_error',
                               n_jobs=-1,
                               verbose=0)
    
    grid_search.fit(X_train, y_train)
    best_model = grid_search.best_estimator_
    #print(f"Best Parameters: {grid_search.best_params_}")
    
    get_scores(best_model,X_test,y_test,log)
    cross_validate_model(best_model,X,y,log)

def cross_validate_model(model, X, y,log):
    cv_scores = cross_val_score(model, X, y, cv=10, scoring='neg_mean_squared_error')
    mean_cv_mse = -cv_scores.mean()  # Negate because cross_val_score returns negative values
    log.append(f"Mean Cross-Validation MSE: {mean_cv_mse}")
    return mean_cv_mse

def decision_tree_regressor(X,y,X_train, X_test, y_train, y_test,modelPath,log,save = False):
    log.append('decision tree regression')
    regressor = DecisionTreeRegressor(random_state=42)
    regressor.fit(X_train, y_train)
    if save: dump(regressor, f"{modelPath}"+'decisionTree_model.joblib')
    get_scores(regressor,X_test,y_test,log)
    cross_validate_model(regressor,X,y,log)
    tune_hyperparameters(X,y,X_train, X_test, y_train, y_test,'decision_tree_regressor',log)

def random_forest_regression(X,y,X_train, X_test, y_train, y_test,modelPath,log,save = False):
    log.append('random forest')
    rf_regressor = RandomForestRegressor(random_state=42)
    rf_regressor.fit(X_train, y_train)
    if save: dump(rf_regressor, f"{modelPath}"+'randomForest_model.joblib')
    rf_r2 = rf_regressor.score(X_test, y_test)
    rf_mse = mean_squared_error(y_test, rf_regressor.predict(X_test))
    log.append(f"Random Forest R²: {rf_r2}")
    log.append(f"Random Forest MSE: {rf_mse}")
    cross_validate_model(rf_regressor,X,y,log)
    tune_hyperparameters(X,y,X_train, X_test, y_train, y_test,'random_forest',log)
    return rf_regressor

def gradient_boosting_regression(X,y,X_train, X_test, y_train, y_test,modelPath,log,save = False):
    log.append('gradient boosting')
    gb_regressor = GradientBoostingRegressor(random_state=42)
    gb_regressor.fit(X_train, y_train)
    if save: dump(gb_regressor, f"{modelPath}"+'gardientBoosting_model.joblib')
    gb_r2 = gb_regressor.score(X_test, y_test)
    gb_mse = mean_squared_error(y_test, gb_regressor.predict(X_test))
    log.append(f"Gradient Boosting R²: {gb_r2}")
    log.append(f"Gradient Boosting MSE: {gb_mse}")
    cross_validate_model(gb_regressor,X,y,log)
    tune_hyperparameters(X,y,X_train, X_test, y_train, y_test,'gradient_boosting',log)
    return gb_regressor

def linear_regression(X,y,X_train, X_test, y_train, y_test,modelPath,log,save = False):
    log.append('linear regression')
    model = LinearRegression()
    model.fit(X_train, y_train)
    if save: dump(model, f"{modelPath}"+'linearRegression_model.joblib')
    get_scores(model,X_test,y_test,log)
    cross_validate_model(model,X,y,log)
    #tune_hyperparameters(X_train, X_test, y_train, y_test,'linear_regression')

def pysr(X,y,X_train, X_test, y_train, y_test,modelPath,log):
    log.append('pysr')
    #model = PySRRegressor(
    #    niterations=100,             # Increase number of iterations for deeper exploration
    #    unary_operators=["sin", "cos", "exp", "log", "sqrt", "abs"],  # Add more unary operators for better flexibility
    #    binary_operators=["+", "-", "*", "/", "^"],  # Add subtraction, division, and exponentiation
    #    constraints={"^": (-1, 1)}, #for the ^ bin op
    #    population_size=200,         # Larger population for more diversity in the search
    #    select_k_features=1,         # Increase to select top-3 features for efficiency
    #    verbosity=0,                 # Show more detailed progress
    #    progress=False               # Optionally, suppress per-iteration progress
    #)
    X_train.columns= [''.join(c for c in x if c.isalnum()) for x in X_train.columns]
    X_test.columns= [''.join(c for c in x if c.isalnum()) for x in X_test.columns]
    model = PySRRegressor(
    niterations=40,
    unary_operators=["sin", "cos", "exp","log"],
    binary_operators=["+", "*"],
    population_size=100,
    constraints={"log": 1},  # Max 1 log per expression (no nested logs) avoids log(log(1))
    run_id=f"{modelPath}",
    #select_k_features=1,
    verbosity=0
    )

    model.fit(X_train, y_train)
    #print(model.sympy())
    get_scores(model,X_test,y_test,log)
    #cross_validate_model(model,X,y)


def m3gp_model(X,y,X_train, X_test, y_train, y_test,modelPath,log,save = False):
    log.append('m3gp')
    model = M3GP(fitnessType="MSE")
    model.fit(X_train, y_train, X_test, y_test) # test is optional
    if save: dump(model, f"{modelPath}"+'linearRegression_model.joblib')
    get_scores(model,X_test,y_test,log)
    cross_validate_model(model,X,y,log)


def plot3D( X, y):
    # axes instance
    fig = plt.figure(figsize=(8,8))
    ax = Axes3D(fig, auto_add_to_figure=False)
    fig.add_axes(ax)
    # get colormap from seaborn
    cmap = ListedColormap(sns.color_palette("husl", 256).as_hex())
    x = X['input0']#np.log1p()
    #print(y)
    z = y#np.log1p(y)
    y = X['input1']#np.log1p()
    #z = regressor.predict(X)
    
    # plot
    sc = ax.scatter(x, y, z, s=40, c=x, marker='o', cmap=cmap, alpha=1)
    ax.set_xlabel('input1')
    ax.set_ylabel('input2')
    ax.set_zlabel('Energy')
    # legend
    plt.legend(*sc.legend_elements(), bbox_to_anchor=(1.05, 1), loc=2)
    plt.show()


    
def save_log_to_file(log, path):
    filename = path+"/log.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for entry in log:
            f.write(f"{entry}\n")
    print(f"Log saved to {filename}")

def readDividedFeatures(files):
    for filename in files: 
        log = []
        log.append("------------------------------------------------------")
        log.append(f"Training model {filename}")
        print(f"Training model {filename}")
        modelPath = createModelsDir(filename)
        df = pd.read_csv(filename)
        df = clean_data(df,False)
        model(df,modelPath+'/models/',log)
        fname = modelPath.split('/')[1]
        subprocess.run(f"cp -r outputs/out/{fname}* {modelPath}/models/pysr", shell=True, capture_output=True, text=True) #copy pysr model to method folder
        save_log_to_file(log,modelPath)
        

def createModelsDir(filename):
    parts = filename.split("/")
    info = "/".join(parts[:2])
    os.makedirs(info+'/models/', exist_ok=True)
    os.makedirs(info+'/models/pysr/', exist_ok=True)
    return info


def getAllFeatures(date):
    original_dir = os.getcwd()
    os.chdir("..")# go up one folder
    os.chdir(f"orchestrator/logs/log_{date}/tmp_files")
    features_paths = get_feature_file_per_subdir_path()
    os.chdir(original_dir)
    files,modelsAvailable = join_method_features(features_paths)
    return (files,modelsAvailable)

    

def join_method_features(features_paths):
    files = []
    data_dict = {}
    modelsAvailable = []
    for features_path in features_paths: 
        parts2 = features_path.split("_")
        method_name = "_".join(parts2[1:])
        modelsAvailable.append("_".join(parts2[0:])) #ArrayList_addAll_int_java_util_Collection_ guarda com o nome da collec
        add_or_concat_df(data_dict,method_name,pd.read_csv(features_paths[features_path]))
    for key in data_dict:
        df = data_dict[key]
        os.makedirs('out/'+key, exist_ok=True)
        df.to_csv('out/'+key+'/'+key+".csv", index=False)
        files.append('out/'+key+'/'+key+".csv")
    createModelsAvailableFile(modelsAvailable)
    return (files,modelsAvailable)

def createModelsAvailableFile(modelsAvailable):
    with open('ModelsAvailable.txt', 'w') as file:
        for model in modelsAvailable:
            file.write(model + '\n')


#def add_or_concat_df(dct, key, df):
#    if key in dct:
#        dct[key] = pd.concat([dct[key], df], ignore_index=True)
#        # as duas linhas de baixo metem 0 nas colunas que têm Nan menos no EnergyUsed
#        cols_to_fill = [col for col in dct[key].columns if col != 'EnergyUsed']
#        dct[key][cols_to_fill] = dct[key][cols_to_fill].fillna(0)
#    else:dct[key] = df.copy()


def add_or_concat_df(dct, key, df):
    if key in dct:
        dct[key] = pd.concat([dct[key], df], ignore_index=True)
        
        # Ensure 'EnergyUsed' is the last column
        cols = [col for col in dct[key].columns if col != 'EnergyUsed']
        if 'EnergyUsed' in dct[key].columns:
            dct[key] = dct[key][cols + ['EnergyUsed']]

        # Fill NaNs with 0, except for 'EnergyUsed'
        cols_to_fill = [col for col in dct[key].columns if col != 'EnergyUsed']
        dct[key][cols_to_fill] = dct[key][cols_to_fill].fillna(0)
    else:
        dct[key] = df.copy()
        
        # Ensure 'EnergyUsed' is the last column
        cols = [col for col in dct[key].columns if col != 'EnergyUsed']
        if 'EnergyUsed' in dct[key].columns:
            dct[key] = dct[key][cols + ['EnergyUsed']]


#vai a cada dir do log/tmp e saca o path do file features.csv -> retorna um dict
def get_feature_file_per_subdir_path(filename="features.csv"):
    cwd = os.getcwd()
    return {
        d: os.path.join(cwd, d, filename or next(f for f in os.listdir(os.path.join(cwd, d))
                                                 if os.path.isfile(os.path.join(cwd, d, f))))
        for d in os.listdir(cwd)
        if os.path.isdir(os.path.join(cwd, d))
           and (filename in os.listdir(os.path.join(cwd, d)) if filename else True)
    }

def check_one_method(method = "size__"):#addAll_java_util_Collection_
    log = []
    filename = method + ".csv"
    print("------------------------------------------------------")
    print(f"Training model {filename}")
    #modelPath = createModelsDir(filename)
    df = pd.read_csv(f'out/{method}/{filename}')
    df = drop_column(df,'Filename')
    #model(df,modelPath,[])
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]
    plot_energy_vs_feature(X,y,'input0')
    #X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    #m3gp_model(X,y,X_train, X_test, y_train, y_test,modelPath,log,save = False)
    #for x in log:
    #    print(x)

def plots(files,fname,date,log_scale):
    for filename in files:
        if fname not in filename:continue
        df = pd.read_csv(filename)
        #associate_df_with_array_size(df,'NBodySystem',fname,date)
        df = clean_data(df,False)
        X = df.iloc[:, :-1]  # All columns except the last one
        y = df.iloc[:, -1]   # Energy column
        print(f'fname -> {filename} | correlations : {correlation(df)}')
        #plot3D(X,y)
        #plot_energy_vs_feature4(X,y,'input0','java.util.concurrent.CopyOnWriteArrayList')
        #plot_by_arr_size(df)
        #plot_energy_vs_feature(X,y,'input0',log_scale)
        #list_type_filter='java.util.concurrent.CopyOnWriteArrayList'



def create_dir_if_not_exists(path):
    if not os.path.exists(path):os.makedirs(path)


def createFilesForExtension(models_available):
    create_dir_if_not_exists("collected_models")
    for model in models_available:
        pysr_model_name = "_".join(model.split("_")[1:])
        pysr_model_path = "out/"+pysr_model_name+"/models/pysr/"+pysr_model_name+"/models/hall_of_fame.csv"
        dst_dir = "collected_models"
        dst_filename = model+".csv"
        dst_path = os.path.join(dst_dir, dst_filename)
        shutil.copyfile(pysr_model_path, dst_path)
    subprocess.run(f"./move_models_to_extension.sh", shell=True, capture_output=True, text=True)

def associate_df_with_array_size(df,collec,fname,date,save=False):
    original_dir = os.getcwd()
    os.chdir("..")# go up one folder
    os.chdir(f"orchestrator/logs/log_{date}/prog_files/{collec}_{fname}")
    all_entries = os.listdir()
    files = [f for f in all_entries if os.path.isfile(f)]
    pattern = r'BenchmarkArgs\[\] arr = new BenchmarkArgs\[(\d+)\]'

    file_array_size = {}
    for filename in files:
        with open(filename, 'r', encoding='utf-8') as file:
            for line_number, line in enumerate(file, start=1):
                match = re.search(pattern, line)
                if match:
                    file_array_size[filename.replace('.java','')] = int(match.group(1))
    df.insert(0, 'arraySize', df['Filename'].map(file_array_size))
    os.chdir(original_dir)
    if save: save_df_to_csv(df,"csv_with_arrSize.csv")

def plot_by_arr_size(df):
    # Define color mapping for arraySize
    color_map = {
        75000: 'green',
        100000: 'blue',
        150000: 'red'
    }

    # Sort dataframe by input0
    df_sorted = df.sort_values(by='input0')

    # Create plot
    plt.figure(figsize=(10, 6))

    # Plot each arraySize group with its own color
    for size, color in color_map.items():
        subset = df_sorted[df_sorted['arraySize'] == size]
        plt.scatter(subset['input0'], subset['EnergyUsed'], label=f'{size}', color=color)

    plt.xlabel('Input')
    plt.ylabel('Energy')
    plt.title('Energy Measured vs Input')
    plt.legend(title='Array Size')
    plt.tight_layout()
    plt.show()

def correlation(df,x = 'input0', y='EnergyUsed'):
    r_pearson, p_value_pearson = pearsonr(df[x], df[y])
    r_spearman, p_value_spearman = spearmanr(df['input0'], df['EnergyUsed'])
    return {'correlation_pearson': r_pearson, 'p_value_pearson': p_value_pearson, 'correlation_spearman': r_spearman, 'p_value_spearman': p_value_spearman}


def get_model_expression(input0):
    return (-7.739528e-6 * math.sin(input0 * -0.81902814)) + 4.2258347e-5


def main():
    #os.makedirs('out/', exist_ok=True)
    date = "2025_06_30"#2025_05_20 2025_06_30
    files,models_available = getAllFeatures(date)
    plots(files,"checkTree_com_template_programsToBenchmark_BinaryTrees_TreeNode_",date,log_scale=False)#equals_java_lang_Object_ createTree_int_
    #readDividedFeatures(files)
    #check_one_method()
    #createFilesForExtension(models_available)

main()

#checkTree_com_template_programsToBenchmark_BinaryTrees_TreeNode_ (input0 * 1.7818553e-7) * ((input0 * input0) + 5.4003377)
#trees_int_ math.exp((input0 + -11.710805) * 0.563765)
#createTree_int_ math.exp((input0 + -19.571716) * 0.6815255) + -0.08256852

#advance_double_ (-7.739528e-6 * math.sin(input0 * -0.81902814)) + 4.2258347e-5
#Approximate_int_ math.sin((input0 * 2.0593527e-6) + 0.0006085703) * input0
#fannkuch_int_ math.exp((input0 + -9.133306) * 2.4944384) + 0.003643311