import xml.etree.ElementTree as ET
import re
from nltk.corpus import stopwords
import pandas as pd
import glob
from tqdm import tqdm
from xmldiff import main
import os
import translators.server as tss
import lxml.html
import sys

STOPWORDS = stopwords.words('english')

class clean():
    """the class for cleaning purpose"""
    def __init__(self, path, infile_brd, infile_table, outfile_brd=None, outfile_table=None):
        self.infile_brd = path + '/MassProduction/' + infile_brd
        self.infile_table = path + '/MassProduction/' + infile_table
        if outfile_brd:
            self.outfile_brd = outfile_brd
        else:
            self.outfile_brd = self.infile_brd.replace('.brd', '_cleaned.brd')
        if outfile_table:
            self.outfile_table = outfile_table
        else:
            self.outfile_table = self.infile_table.replace('.txt', '_cleaned.txt')
        self.var_phrase_map = dict()
        self.var_name_map = dict()
        self.table_new = None
        self.table_new_index_list = None

    def clean_name(self, s, convert_to_lower=True):
        """create name for variables in .brd"""
        try:
            s = re.sub('<[^<]+?>', '', s) # markup
            s = re.sub('[^0-9a-zA-Z_\s]', '', s) # keep alnum
            s = re.sub('\t\n\r', '', s) # remove tab, line break, carriage return
            s = ' '.join(s.split()) # remove redundant whitespace
            return s.lower() if convert_to_lower else s
        except:
            s = s
            return s
    
    def clean_phrase(self, s, convert_to_lower=False):
        """remove unnecessary part in value"""
        if(s is None or s == '' or s==' '):
            return None
        s = re.sub('\t\n\r', '', s) # remove tab, line break, carriage return
        s = ' '.join(s.split()) # remove redundant whitespace
        return s.lower() if convert_to_lower else s

    def find_hash(self, s):
        """find hash-like variable"""
        if(s is None or s == '' or s == ' '):
            return False
        # replace "%(" and "%)" to detect whether the variable is a hash-like
        s = re.sub('%\(', '', s) # "\(" is for re to search "("
        s = re.sub('\)%', '', s)
        return s.lstrip('-').isdigit() # ignore "-" in the variable 
    
    def change_var(self, old_name, signature='_', keep_n_words=4):
        """change hash-like variable's name in df"""
        # print(old_name)
        if old_name in self.var_name_map:
            return self.var_name_map[old_name]
        else:
            phrase = self.table_new.loc[old_name].iloc[0] # find the first pharse in the mass production table
            # print(phrase, len(phrase))
            # print(type(phrase))
            if (old_name is None or old_name == ''):
                return ''
            elif (pd.isnull(phrase) or len(phrase) == 0):
                self.var_name_map[old_name] = old_name
                return old_name
            the_clean_phrase = self.clean_phrase(phrase) 
            h = signature + '_' + '_'.join([word for word in self.clean_name(the_clean_phrase).split(' ') if word not in STOPWORDS][:keep_n_words])
            v = '%(' + str(h) + ')%'
            self.var_name_map[old_name] = v
            self.table_new.rename(index={old_name:v}, inplace=True) # dict key: variable value, dict value: variable name
            return v
    
    def make_var(self, phrase, signature='_', keep_n_words=4):
        """create variable-value pair"""
        if (phrase is None or phrase == ''):
            return ''
        the_clean_phrase = self.clean_phrase(phrase) # clean the value(phrase)
        # if the variable in self.var_phrase_map
        if the_clean_phrase in self.var_phrase_map: 
            return self.var_phrase_map[the_clean_phrase]
        # else create one
        else:
            h = signature + '_' + '_'.join([word for word in self.clean_name(the_clean_phrase).split(' ') if word not in STOPWORDS][:keep_n_words])
            v = '%(' + str(h) + ')%' # create variable name
            self.var_phrase_map[the_clean_phrase] = v # dict key: value, dict value: variable
            return v
        
    def find_var(self, txt):
        pattern_variable = "%\((.*?)\)%"
        match_variable = [match for match in re.findall(pattern_variable, str(txt))]
        if match_variable:
            for i in range(len(match_variable)):
                variable = "%(" + str(match_variable[i]) + ")%"
                txt = txt.replace(variable, ' ')
            if re.search('[a-zA-Z]', txt):
                return True
            else:
                return False
        else:
            return True
        
    def process_txt(self, txt, element, tag, count):
        """process txt"""
        # if txt is empty
        if self.clean_phrase(txt) is None or self.clean_phrase(txt) == '':
            return
        # elif txt is already in the mass production table and it is not a hash-like
        elif txt in self.table_new_index_list and self.find_hash(txt) is False:
            return
        # elif txt is already in the mass production table and there is no need to be proceeded
        elif self.find_var(txt) is False and self.find_hash(txt) is False:
            return
        # elif txt is already in the mass production table and it is a hash-like
        elif txt in self.table_new_index_list and self.find_hash(txt) is True:
            if tag == 'Input':
                element[0].text = self.change_var(txt, signature=tag+'_'+str(count))
            else:
                element.text = self.change_var(txt, signature=tag+'_'+str(count))
            return
        # else create a variable name for the value
        else:
            if tag == 'Input':
                element[0].text = self.make_var(txt, signature=tag+'_'+str(count))
            else:
                element.text = self.make_var(txt, signature=tag+'_'+str(count))
            return 
    
    def iterate_generic(self, tag: str, root):
        """replace pharse with variable,
            txt should be %% type or a pharse"""
        count = 1
        for element in root.iter(tag):
            # print(tag)
            if tag == 'Input' and element[0].tag == 'value': # find input value
                txt = element[0].text
                self.process_txt(txt, element, tag, count)
            else:
                txt = element.text
                self.process_txt(txt, element, tag, count)
            count += 1

    def clean_file(self):
        """read the tags and call all functions above"""
        tree = ET.parse(self.infile_brd)
        print("mass production brd input read")
        print("path: " + self.infile_brd)
        root = tree.getroot()

        self.table_new = pd.read_csv(self.infile_table, sep="\t", index_col=0, keep_default_na=False)
        self.table_new_index_list = self.table_new.index.tolist()
        print("mass production table input read")
        print("path: " + self.infile_table)

        tags = ['hintMessage', 'successMessage', 'buggyMessage', 'label', 'Input']
        for tag in tags:
            self.iterate_generic(tag, root) 

        # create new dataframe and concat it with the latest mass production table
        df_new = pd.DataFrame(self.var_phrase_map.keys(), index = list(self.var_phrase_map.values()))
        df_dup = pd.concat([df_new.T]*len(self.table_new.columns)).T
        df_dup.columns = self.table_new.columns
        df_mix = pd.concat([self.table_new, df_dup])
        df_mix.index.name = self.table_new.index.name

        # export the csv
        df_mix.to_csv(self.outfile_table, encoding="utf-8", sep="\t")
        print("mass production table output finished")
        print("path: " + self.outfile_table)

        # export the brd
        output = open(self.outfile_brd, 'w+b')
        output.write(b'<?xml version="1.0" standalone="yes"?>\n\n')
        tree.write(output)
        print("mass production brd output finished")
        print("path: " + self.outfile_table)

        return self.table_new, df_mix

class validate():
    """the class for validation purpose"""
    def __init__(self, path=None, old_folder=None, new_folder=None):
        if old_folder:
            self.old_folder = old_folder
        else:
            try:
                self.old_folder = path + "/FinalBRDs/"
            except:
                print("please enter path")
        if new_folder:
            self.new_folder = new_folder
        else:
            try:
                self.new_folder = path + "/FinalBRDs/CleanedBRDs/"
            except:
                print("please enter path")

    def check(self, old_brd, new_brd):
        """use ET.parse to validate"""
        old = ET.parse(old_brd)
        new = ET.parse(new_brd)
        old_text = old.getroot().itertext()
        new_text = new.getroot().itertext()
        set_old = set(old_text)
        set_new = set(new_text)
        if set_old == set_new:
            res = "True"
        else:
            res = "False"
        return set_old, set_new, res

    def check_xmldiff(self, old_brd, new_brd):
        """use xmldiff to validate"""
        diff = main.diff_files(old_brd, new_brd)
        if len(diff) == 0:
            res = "True"
        else:
            res = "False"
        return diff, res
    
    def validate_file(self):
        fs_brd = glob.glob(self.old_folder + "*")
        for old_brd in tqdm(fs_brd, position=0, leave=True):
            new_brd = self.new_folder + old_brd.split("\\", 1)[-1]
            if os.path.exists(new_brd):
                new_brd = new_brd
            elif os.path.exists(new_brd.replace('Problem', '')):
                new_brd = new_brd.replace('Problem', '')
            elif os.path.exists(new_brd.replace(old_brd.split("\\", 1)[-1], "Problem"+old_brd.split("\\", 1)[-1])):
                new_brd = new_brd.replace(old_brd.split("\\", 1)[-1], "Problem"+old_brd.split("\\", 1)[-1])
            else:
                print(old_brd.split("\\", 1)[-1], " cannot find reference")
                continue
            try:
                _, _, res_tree = self.check(old_brd, new_brd)
                _, res_diff = self.check_xmldiff(old_brd, new_brd)
                print(old_brd.split("\\", 1)[-1], res_tree, res_diff)
            except Exception as e: 
                print("error", old_brd.split("\\", 1)[-1], e)

class mass_produce:
    """the class for mass production purpose"""
    def __init__(self, path, infile_brd, infile_table, outfile_folder=None):
        self.infile_brd = path + '/MassProduction/' + infile_brd
        self.infile_table = path + '/MassProduction/' + infile_table
        if outfile_folder:
            self.outfile_folder = outfile_folder
        else:
            self.outfile_folder = path +'/FinalBRDs/CleanedBRDs/'
        if os.path.exists(self.outfile_folder):
            pass
        else:
            os.makedirs(self.outfile_folder)
            
    def replace_var(self):
        """replace variable with value in the latest mass production table"""
        table_clean = pd.read_csv(self.infile_table, sep="\t", index_col=0, keep_default_na=False)
        for column in range(table_clean.shape[1]):
            for row in range(table_clean.shape[0]):
                content_new = str(table_clean.iloc[row, column])
                pattern_variable = "%\((.*?)\)%"
                # count the number of the replacement in one variable(content_new)
                match_variable = [match for match in re.findall(pattern_variable, str(content_new))]
                for i in range(len(match_variable)):
                    # find the variable
                    variable = "%(" + str(match_variable[i]) + ")%"
                    # find the corresponding column name, and then find the value
                    column_name = table_clean.columns[column]
                    try:
                        value = table_clean.loc[variable, column_name] 
                        # print(variable, value)
                        content_new = content_new.replace(variable, value)
                        table_clean.iloc[row, column] = content_new
                    except:
                        print(column_name, variable + " doesn't exist")
        return table_clean

    def function_format(self, content_new):
        pattern_function = "<%(.*?)%>"
        # count the number of functions in one variable(content_new)
        match_function = [match for match in re.findall(pattern_function, str(content_new))]
        if match_function:
            for i in range(len(match_function)):
                function = "<%" + str(match_function[i]) + "%>"
                match_function[i] = match_function[i].replace('"', "&quot;")
                function_new = "&lt;%" + str(match_function[i]) + "%&gt;"
                content_new = content_new.replace(function, function_new)
        return content_new
    
    def mass_produce_file(self):
        """iterate and mass produce all the brds"""
        table_clean = self.replace_var()
        for i in range(len(table_clean.columns)):
            column_name = table_clean.columns[i]
            fout = self.outfile_folder + str(table_clean.columns[i]) + ".brd" # can change the path of clean brd here
            count_line = 0
            count_text = 0
            count_name = 0
            with open(self.infile_brd, 'r', encoding='utf-8') as infile, open(fout, 'w+', encoding='utf-8') as outfile:
                for line in infile:
                    line = line.replace('\r', '')
                    line_str = str(line)
                    # replace massproduce
                    if count_name == 0:
                        pattern_problem_name_1 = "<ProblemName>(.*?)</ProblemName>"
                        match_problem_name_1 = [match for match in re.findall(pattern_problem_name_1, str(line_str))]
                        pattern_problem_name_2 = "<ProblemName />"
                        match_problem_name_2 = [match for match in re.findall(pattern_problem_name_2, str(line_str))]
                        problem_name = "<ProblemName>" + str(column_name) + "</ProblemName>"
                        if match_problem_name_1:
                            line_str = line_str.replace(match_problem_name_1[0], str(column_name))
                            # print(line_str)
                            count_name += 1
                        elif match_problem_name_2:
                            line_str = line_str.replace(match_problem_name_2[0], problem_name)
                            # print(line_str)
                            count_name += 1
                        else:
                            pass
                    # replace text in first node
                    if count_text == 0:
                        pattern_first_node_1 = "<text>(.*?)</text>"
                        match_first_node_1 = [match for match in re.findall(pattern_first_node_1, str(line_str))]
                        pattern_first_node_2 = "<text />"
                        match_first_node_2 = [match for match in re.findall(pattern_first_node_2, str(line_str))]
                        node_name = "<text>" + str(column_name) + "</text>"
                        if match_first_node_1:
                            line_str = line_str.replace(match_first_node_1[0], str(column_name))
                            count_text += 1
                        elif match_first_node_2:
                            line_str = line_str.replace(match_first_node_2[0], node_name)
                            count_text += 1
                        else:
                            pass
                    # count the number of the replacement in one variable(line_str)
                    pattern_variable = "%\((.*?)\)%"
                    match_variable = [match for match in re.findall(pattern_variable, str(line_str))]
                    if match_variable == []:
                        line_str = line_str
                    else:
                        for j in range(len(match_variable)):
                            # find the variable
                            variable = "%(" + str(match_variable[j]) + ")%"
                            # find the corresponding column name, and then find the value
                            try:
                                value = table_clean.loc[variable, column_name]
                                line_str = line_str.replace(variable, value)
                                line_str = self.function_format(line_str)
                                # line_str = line_str.replace(variable, value).replace("<%", "&lt;%").replace("%>", "%&gt;")
                            except:
                                print(column_name, variable + " doesn't exist")
                    count_line += 1
                    outfile.write(line_str)
                print(fout.split("/")[-1] + " finished")

class translate():
    """the class for translation table purpose"""
    def __init__(self, path, infile_table, path_output=None, path_no_mark=None, TARGET_LANG='es', path_ref=None):
        self.path_new = path + '/MassProduction/' + infile_table
        self.path_ref = path_ref
        self.TARGET_LANG = TARGET_LANG        
        if path_output:
            self.path_output = path_output
        else:
            self.path_output = self.path_new.replace('.txt', '_translated[marked].txt')
        if path_no_mark:
            self.path_no_mark = path_no_mark
        else:
            self.path_no_mark = self.path_new.replace('.txt', '_translated.txt')


    def replace_string(self, formula, column, row):
        """replace the string in the formula"""
        pattern_string = '"(.*?)"'
        match_string = [match for match in re.findall(pattern_string, formula)]
        if match_string:
            for i in range(len(match_string)):
                string = str(match_string[i])
                formula = formula.replace(string, self.replace_variable(string, column, row)) 
        return formula

    def translate_string(self, formula):
        """translate the string in the formula"""
        pattern_string = '"(.*?)"'
        match_string = [match for match in re.findall(pattern_string, formula)]
        if match_string:
            for i in range(len(match_string)):
                string = str(match_string[i])
                if string == '':
                    pass
                else:
                    try:
                        translation = tss.google(string, from_language='en', to_language=self.TARGET_LANG)
                    except:
                        translation = 'error'
                    formula = formula.replace(string, translation) 
        return formula

    def replace_formula(self, content_new, column=None, row=None, is_translate=False, replacement="#"):
        """replace the formula in the content_new"""
        replacement_sign = replacement
        replacement_formula_dic = {}
        pattern_formula = "<%(.*?)%>"
        match_formula = [match for match in re.findall(pattern_formula, str(content_new))]
        if match_formula:
            for i in range(len(match_formula)):
                old_formula = match_formula[i]
                if '"' in old_formula:
                    if is_translate:
                        formula = self.translate_string(old_formula)
                    else:
                        formula = self.replace_string(old_formula, column, row)
                    final_formula = str(formula)
                else:
                    final_formula = str(old_formula)
                replacement = replacement_sign + str(i)
                replacement_formula_dic[replacement] = '<%' + final_formula + '%>'
                content_new = content_new.replace('<%' + old_formula + '%>', replacement)
        return content_new, replacement_formula_dic

    def replace_variable(self, content_new, column, row):
        """input: content_new(string), column, row;
            output: content_new(string);
            replace variable with value in the latest mass production table"""
        table_clean = pd.read_csv(self.path_new, sep="\t", index_col=0, keep_default_na=False)
        flag = True
        while flag:
            pattern_variable = "%\((.*?)\)%"
        # count the number of the replacement in one variable(content_new)
            match_variable = [match for match in re.findall(pattern_variable, str(content_new))]
            if match_variable:
                for i in range(len(match_variable)):
                    # find the variable
                    variable = "%(" + str(match_variable[i]) + ")%"
                    # find the corresponding column name, and then find the value
                    column_name = table_clean.columns[column]
                    try:
                        value = table_clean.loc[variable, column_name] 
                        # print(variable, value)
                        content_new = content_new.replace(variable, value)
                        table_clean.iloc[row, column] = content_new
                    except:
                        print(column_name, variable + " doesn't exist")
                        flag = False
            else:
                flag = False
        if flag == False:
            return content_new
        else:
            content_new = self.replace_variable(content_new, column, row)
    
    def create_table(self):
        table_clean = pd.read_csv(self.path_new, sep="\t", index_col=0, keep_default_na=False)

        # Change column name
        table_clean_col_list = []
        for i in table_clean:
            table_clean_col_list.append(i)
            table_clean_col_list.append(i + '_' + self.TARGET_LANG)

        # Create a new table, with the column from the Greg's mass production table and the index from the latest mass production table
        table_translated = pd.DataFrame(columns=table_clean_col_list, index=table_clean.index)
        table_translated_clean = pd.DataFrame(columns=table_clean_col_list, index=table_clean.index)

        return table_translated, table_translated_clean
    
    def translate_file(self):
        if self.path_ref is None:
            table_old = None
        else:
            # read the Greg's mass production table
            table_old = pd.read_csv(self.path_ref, header = None)
            # skip some rows, because they are translation for HTML elements
            header_index = table_old.index[table_old[0] == 'Problem Name'].to_list()
            # reload the csv
            table_old = pd.read_csv(self.path_ref, header = header_index)

        table_clean = pd.read_csv(self.path_new, sep="\t", index_col=0, keep_default_na=False)
        table_translated, table_translated_clean = self.create_table()
        
        # find the translation of the latest mass production table from the Greg's mass production table 
        google_dict = {}
        for column in range(table_clean.shape[1]):
            column_name = table_clean.columns[column]
            print(column_name)
            column_num = table_translated.columns.get_loc(column_name)
            for row in range(table_clean.shape[0]):
                # get the location
                content_new = str(table_clean.iloc[row, column])
                # skip the startnode
                if table_clean.index[row] == '%(startStateNodeName)%':
                    print("skip '%(startStateNodeName)%'")
                    # write the english column
                    table_translated[column_name].iloc[row] = content_new
                    table_translated_clean[column_name].iloc[row] = content_new
                    content_translated = content_new
                    content_translated_clean = content_new
                # skip the graphic
                elif 'graphic' in table_clean.index[row]:
                    print("skip" +"'"+ table_clean.index[row]+"'")
                    # write the english column
                    table_translated[column_name].iloc[row] = content_new
                    table_translated_clean[column_name].iloc[row] = content_new
                    content_translated = content_new
                    content_translated_clean = content_new
                # digit or empty, keep the original
                elif re.match(r"^(?!-0?(\.0+)?$)-?(0|[1-9]\d*)?(\.\d+)?(?<=\d)$", content_new) or content_new == '':
                    # print("digital or empty")
                    table_translated[column_name].iloc[row] = content_new
                    table_translated_clean[column_name].iloc[row] = content_new
                    content_translated = content_new
                    content_translated_clean = content_new                    
                else:
                    # replace
                    # judge whether a formula inside the content new
                    pattern_formula = "<%(.*?)%>"
                    # count the number of the replacement in one variable(content_new)
                    match_formula = [match for match in re.findall(pattern_formula, str(content_new))]
                    if match_formula:
                        content_new, replacement_formula_dic = self.replace_formula(content_new, column, row)
                    else:
                        replacement_formula_dic = None
                    pattern_variable = "%\((.*?)\)%"
                    content_new = self.replace_variable(content_new, column, row)
                    match_variable = [match for match in re.findall(pattern_variable, str(content_new))]
                    if bool(replacement_formula_dic) is False:
                        pass
                    else:
                        for key, value in replacement_formula_dic.items():
                            content_new = content_new.replace(key, value)
                    table_translated[column_name].iloc[row] = content_new
                    table_translated_clean[column_name].iloc[row] = content_new
                    # translate
                    # search in dict
                    if content_new in google_dict:
                        # print("find translation in dict")
                        content_translated = '[google]' + google_dict[content_new]
                        content_translated_clean = google_dict[content_new]
                    # translate in google
                    elif table_old is None or table_old.columns[(table_old == content_new).any()].empty:
                        # print("use google translation")
                        # print(content_new)
                        if match_formula:
                            content_new, translation_formula_dic = self.replace_formula(content_new, is_translate=True)
                        else:
                            translation_formula_dic = None
                        try:
                            translation = tss.google(content_new, from_language='en', to_language=self.TARGET_LANG)
                        except:
                            translation = 'error'
                            print('error, to be translated:', content_new)
                        if bool(translation_formula_dic) is False:
                            pass
                        else:
                            for key, value in translation_formula_dic.items():
                                content_new = content_new.replace(key, value)
                                translation = translation.replace(key, value)
                        content_translated = '[google]' + translation
                        content_translated_clean = translation
                        google_dict[content_new] = translation 
                    # find translation in old table
                    else:
                        # print("find translation in sheet")
                        column_name_old = table_old.columns[(table_old == content_new).any()][0]
                        column_num_old = table_old.columns.get_loc(column_name_old)
                        content_translated = table_old[table_old[column_name_old] == content_new].iloc[0, column_num_old+1]
                        content_translated_clean = table_old[table_old[column_name_old] == content_new].iloc[0, column_num_old+1]  
                table_translated.iloc[row, column_num+1] = content_translated
                table_translated_clean.iloc[row, column_num+1] = content_translated_clean  
        # export the csv
        table_translated.to_csv(self.path_output, encoding="utf-8", sep="\t")
        table_translated_clean.to_csv(self.path_no_mark, encoding="utf-8", sep="\t")

class translate_html():
    """the class for translation HTML purpose"""
    def __init__(self, path, infile_html, path_output=None, TARGET_LANG='es'):
        self.input_path = path + '/HTML/' + infile_html
        if path_output:
            self.output_path = path_output
        else:
            self.output_path = self.input_path.replace('.html', '_' + TARGET_LANG + '.html')
        self.TARGET_LANG = TARGET_LANG 

    def translate_file(self):

        print("begin HTML translation")
        tree = lxml.html.parse(self.input_path)
        root = tree.getroot()

        tags = ['div', 'th', 'span']

        for tag in tags:
            for element in root.iter(tag):
                text = element.text
                try:
                    if text.isspace() or text is None or text == '':
                        pass
                    elif text.isdigit():
                        pass
                    else:
                        element.text = tss.google(text, from_language='en', to_language=self.TARGET_LANG)
                except:
                    pass

        output = open(self.output_path, 'w+b')
        tree.write_c14n(output)
        output.close()
        print("finish HTML translation")

class translate_xml():
    """the class for translation XML purpose"""
    def __init__(self, path, infile_xml='package.xml', path_output=None, path_translation = None, path_ref=None, TARGET_LANG='es'):
        self.input_path = path + '/' + infile_xml
        if path_output:
            self.output_path = path_output
        else:
            # self.output_path = self.input_path.replace('.xml', '_' + TARGET_LANG + '.xml')
            self.output_path = self.input_path
        rename_path = self.input_path.replace('.xml', '_en.xml')
        os.rename(self.input_path, rename_path)
        self.input_path = rename_path
        self.TARGET_LANG = TARGET_LANG 
        self.path_translation = path_translation
        self.path_ref = path_ref

    def translate_file(self):
        TARGET_LANG = self.TARGET_LANG
        dict = {}
        try:
            table_clean = pd.read_csv(self.path_translation, sep="\t", index_col=0, keep_default_na=False)
            for i in table_clean.index:
                if "ruleName" in i:
                    key_column = table_clean.columns[0]
                    value_column = table_clean.columns[1]
                    dict[table_clean.loc[i, key_column]] = table_clean.loc[i, value_column]
            print("translated table is used")
        except:
            pass
        try:
            table_old = pd.read_csv(self.path_ref, sep=",")
            for i in table_old.index:
                if i < table_old.index[table_old.iloc[:, 0] == 'Problem Name'].to_list()[0]:
                    key_column = table_old.columns[0]
                    value_column = table_old.columns[1]
                    dict[table_old.loc[i, key_column]] = table_old.loc[i, value_column]
            print("referenced table is used")
        except:
            pass
        print("begin XML translation")
        tree = ET.parse(self.input_path)
        root = tree.getroot()
        root.attrib['label'] = root.attrib['label'] + 'es'
        try:
            if root.attrib['description'] in dict:
                translation = dict[root.attrib['description']]
            else:
                translation = tss.google(root.attrib['description'], from_language='en', to_language=self.TARGET_LANG)
                dict[root.attrib['description']] = translation
            root.attrib['description'] = translation[0:253]
        except:
            pass
        for child in root:
            #  children are Problems, Problemsets, Assets
            for i in range(len(child)):
                if child[i].tag == 'Problem':
                    problem = child[i]
                    try:
                        if problem.attrib['label'] in dict:
                            translation = dict[problem.attrib['label']]
                        else:
                            translation = tss.google(problem.attrib['label'], from_language='en', to_language=TARGET_LANG)
                            dict[problem.attrib['label']] = translation
                        problem.attrib['label'] = translation
                        if problem.attrib['description'] in dict:
                            translation = dict[problem.attrib['description']]
                        else:
                            translation = tss.google(problem.attrib['description'], from_language='en', to_language=TARGET_LANG)
                            dict[problem.attrib['description']] = translation
                        problem.attrib['description'] = translation[0:253]
                    except:
                        pass
                    problem.attrib['model_file'] = child[i].attrib['model_file'].replace('.brd', '_' + 'es' +'.brd')
                    problem.attrib['student_interface'] = child[i].attrib['student_interface'].replace('.html', '_' + 'es' +'.html')
                    for j in range(len(problem)):
                        if problem[j].tag == "Skills":
                            skills = problem[j]
                            for k in range(len(skills)):
                                skill = skills[k]
                                try:
                                    if skill.attrib['category'] in dict:
                                        category = dict[skill.attrib['category']]
                                    else:
                                        category = skill.attrib['category'] + '-' + TARGET_LANG
                                        dict[skill.attrib['category']] = category
                                except:
                                    pass
                                skill.attrib['category'] = str(category)
                elif child[i].tag == 'ProblemSet':
                    problemset = child[i]
                    problemset.attrib['label'] = problemset.attrib['label'] + 'es'
                    try:
                        if problemset.attrib['description'] in dict:
                            translation = dict[problemset.attrib['description']]
                        else:
                            translation = tss.google(problemset.attrib['description'], from_language='en', to_language=TARGET_LANG)
                            dict[problemset.attrib['description']] = translation
                        problemset.attrib['description'] = translation[0:253]
                    except:
                        pass
                    for j in range(len(problemset)):
                        if problemset[j].tag == "Skills":
                            skills = problemset[j]
                            for k in range(len(skills)):
                                skill = skills[k]
                                try:
                                    if skill.attrib['category'] in dict:
                                        category = dict[skill.attrib['category']]
                                    else:
                                        category = skill.attrib['category'] + '-' + TARGET_LANG
                                        dict[skill.attrib['category']] = category
                                except:
                                    pass
                                skill.attrib['category'] = str(category)
                                try:
                                    if skill.attrib['description'] in dict:
                                        translation = dict[skill.attrib['description']]
                                    else:
                                        translation = tss.google(skill.attrib['description'], from_language='en', to_language=TARGET_LANG)
                                        dict[skill.attrib['description']] = translation
                                except:
                                    pass
                                skill.attrib['description'] = translation[0:253]
        with open(self.output_path, 'w+b') as outfile:
            outfile.write(b'<?xml version="1.0" standalone="yes"?>\n')
            tree.write(outfile, encoding='utf-8')
        print("finish XML translation")

if __name__ == "__main__":
    mode = sys.argv[1]
    path = sys.argv[2]
    if mode == 'all':
        print("do it all")
        for arg in sys.argv[3:]:
            # print(arg)
            _, file_extension = os.path.splitext(arg)
            if file_extension == '.brd':
                html_brd = arg
            elif file_extension == '.txt':
                html_table = arg
            elif file_extension == '.html':
                infile_html = arg
            elif file_extension == '.csv':
                ref_table = arg
            else:
                TARGET_LANG = arg
        
        cleaned_brd = html_brd.replace(".brd", "_cleaned.brd")
        cleaned_table = html_table.replace(".txt", "_cleaned.txt")
        translated_table = cleaned_table.replace(".txt", "_translated.txt")

        try:
            ref_table
        except:
            ref_table = None
        
        try:
            TARGET_LANG
        except:
            TARGET_LANG = 'es'

        print("clean task ------")
        clean_res = clean(path, html_brd, html_table)
        _, _ = clean_res.clean_file()
        print("mass produce for clean task ------")
        mass_produce_clean_res = mass_produce(path, cleaned_brd, cleaned_table)
        mass_produce_clean_res.mass_produce_file()
        print("validate for clean task ------")
        validate_clean_res = validate(path)
        validate_clean_res.validate_file()
        print("translate table task ------")
        translate_clean_res = translate(path, cleaned_table, TARGET_LANG=TARGET_LANG, path_ref=ref_table)
        translate_clean_res.translate_file()
        print("mass produce for translation task ------")
        mass_produce_translate_res = mass_produce(path, cleaned_brd, translated_table)
        mass_produce_translate_res.mass_produce_file()
        print("validate for translation task ------")
        validate_clean_res = validate(path)
        validate_clean_res.validate_file()
        # print("translate html task ------")
        # translate_clean_html = translate_html(path, infile_html, TARGET_LANG=TARGET_LANG)
        # translate_clean_html.translate_file()
        # print("translate xml task ------")
        # translate_clean_xml = translate_xml(path, path_translation = translated_table, path_ref=ref_table, TARGET_LANG=TARGET_LANG)
        # translate_clean_xml.translate_file()




# python general_new.py all "./HTML_folder/7.17 ESP HTML/7.17 ESP HTML" 7-17_finalTemplate_new.brd 7-17_finalMassProduction_new.txt 7.17.html "./Greg_table_folder/7.17 - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.20 ESP HTML/6.20 ESP HTML" 6-20.brd 6-20.txt 6.20.html "./Greg_table_folder/6.20 - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.10 ESP HTML/6.10 ESP HTML" finalTemplateNew.brd finalMassProdtable.txt 6.10.html "./Greg_table_folder/6.10 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/7.06 ESP HTML/7.06 ESP HTML" 7_06.brd 7_06.txt 7.06.html "./Greg_table_folder/7.06 - Sheet1.csv"

# python general_new.py all "./HTML_folder/7.10 ESP HTML/7.10 ESP HTML" 7_10.brd 7_10.txt 7.10.html "./Greg_table_folder/7.10 - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.02 ESP HTML/6.02 ESP HTML" 6-02.brd 6-02.txt 6.02.html "./Greg_table_folder/6.02 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.17 ESP HTML/6.17 ESP HTML" 6_17.brd 6_17.txt 6.17.html "./Greg_table_folder/6.17 Translation - Sheet2.csv"

# python general_new.py all "./HTML_folder/6.27 ESP HTML/6.27 ESP HTML" 6-27.brd 6-27.txt 6.27.html "./Greg_table_folder/6.27 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/7.05 ESP HTML/7.05 ESP HTML" 7-05_finalTemplate.brd 7-05_finalMassProduction.txt 7.05.html "./Greg_table_folder/7.05 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/7.07 ESP HTML/7.07 ESP HTML" 7-07_finalTemplate.brd 7-07_finalMassProduction.txt 7.07.html "./Greg_table_folder/7.07 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/8.15 ESP HTML/8.15 ESP HTML" 8-15_new.brd 8-15.txt 8.15.html "./Greg_table_folder/8.15 - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.01 ESP HTML/6.01 ESP HTML" 6-01-4.brd 6-01-4.txt 6.01-4.html "./Greg_table_folder/6.01 - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.01 ESP HTML/6.01 ESP HTML" 6-01-5.brd 6-01-5.txt 6.01-5.html "./Greg_table_folder/6.01 - Sheet2.csv"

# python general_new.py all "./HTML_folder/6.05 ESP HTML/6.05 ESP HTML" 6_5.brd 6_5.txt 6.05.html "./Greg_table_folder/6.05 - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.06 ESP HTML/6.06 ESP HTML" finalTemplateNew.brd finalMassProdtable.txt 6.06.html "./Greg_table_folder/6.06 Translation - Sheet2.csv"

# python general_new.py all "./HTML_folder/6.07 ESP HTML/6.07 ESP HTML" 6_07_bank-account_finalTemplate.brd 6_07_bank-account_finalMassProduction.txt 6.07.html "./Greg_table_folder/6.07 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.07 ESP HTML/6.07 ESP HTML" 6_07_birthday_finalTemplate.brd 6_07_birthday_finalMassProduction.txt 6.07.html "./Greg_table_folder/6.07 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.07 ESP HTML/6.07 ESP HTML" 6_07_entertainment_finalTemplate.brd 6_07_entertainment_finalMassProduction.txt 6.07.html "./Greg_table_folder/6.07 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.07 ESP HTML/6.07 ESP HTML" 6_07_fleece_finalTemplate.brd 6_07_fleece_finalMassProduction.txt 6.07.html "./Greg_table_folder/6.07 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.07 ESP HTML/6.07 ESP HTML" 6_07_gardening_finalTemplate.brd 6_07_gardening_finalMassProduction.txt 6.07.html "./Greg_table_folder/6.07 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.07 ESP HTML/6.07 ESP HTML" 6_07_post-office_finalTemplate.brd 6_07_post-office_finalMassProduction.txt 6.07.html "./Greg_table_folder/6.07 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.07 ESP HTML/6.07 ESP HTML" 6_07_softball_finalTemplate.brd 6_07_softball_finalMassProduction.txt 6.07.html "./Greg_table_folder/6.07 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.07 ESP HTML/6.07 ESP HTML" 6_07_vacation_finalTemplate.brd 6_07_vacation_finalMassProduction.txt 6.07.html "./Greg_table_folder/6.07 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.08 ESP HTML/6.08 ESP HTML" finalTemplateNew.brd finalMassProdtable.txt 6.08.html "./Greg_table_folder/6.08 Translation - Sheet2.csv"

# python general_new.py all "./HTML_folder/6.11 ESP HTML/6.11 ESP HTML" ADDITIONfinalTemplate.brd ADDITIONfinalMassProdtable.txt 6.11.html "./Greg_table_folder/6.11 Translation - merge.csv"

# python general_new.py all "./HTML_folder/6.11 ESP HTML/6.11 ESP HTML" STARTfinalTemplate.brd STARTfinalMassProdtable.txt 6.11.html "./Greg_table_folder/6.11 Translation - merge.csv"

# python general_new.py all "./HTML_folder/6.11 ESP HTML/6.11 ESP HTML" SUBTRACTIONfinalTemplate.brd SUBTRACTIONfinalMassProdtable.txt 6.11.html "./Greg_table_folder/6.11 Translation - merge.csv"

# python general_new.py all "./HTML_folder/6.14 ESP HTML/6.14 ESP HTML" 6-14_finalTemplate.brd 6-14_finalMassProduction.txt 6.14.html "./Greg_table_folder/6.14 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.15 ESP HTML/6.15 ESP HTML" 6-15_finalTemplate.brd 6-15_finalMassProduction.txt 6.15.html "./Greg_table_folder/6.15 - Sheet2.csv"

# python general_new.py all "./HTML_folder/6.16 ESP HTML/6.16 ESP HTML" 6-16a_finalTemplate.brd 6-16a_finalMassProduction.txt 6.16a.html "./Greg_table_folder/6.16 A - Sheet2_merge.csv"

# python general_new.py all "./HTML_folder/6.16 ESP HTML/6.16 ESP HTML" 6-16b-gloss_finalTemplate.brd 6-16b-gloss_finalMassProduction.txt 6.16b.html "./Greg_table_folder/6.16 A - Sheet2_merge.csv"

# python general_new.py all "./HTML_folder/6.18 ESP HTML/6.18 ESP HTML" 6-18_finalTemplate.brd 6-18_finalMassProduction.txt 6.18.html "./Greg_table_folder/6.18 - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.19 ESP HTML/6.19 ESP HTML" 6-19.brd 6-19.txt 6.19.html "./Greg_table_folder/6.19 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.21 ESP HTML/6.21 ESP HTML" 6_21.brd 6_21.txt 6.21.html "./Greg_table_folder/6.21 - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.24 ESP HTML/6.24 ESP HTML" 6-24-1_finalTemplate.brd 6-24-1_finalMassProduction.txt 6.24.html "./Greg_table_folder/6.24 Translation - Sheet1_merge.csv"

# python general_new.py all "./HTML_folder/6.24 ESP HTML/6.24 ESP HTML" 6-24-2_finalTemplate.brd 6-24-2_finalMassProduction.txt 6.24.html "./Greg_table_folder/6.24 Translation - Sheet1_merge.csv"

# python general_new.py all "./HTML_folder/6.24 ESP HTML/6.24 ESP HTML" 6-24-3_finalTemplate.brd 6-24-3_finalMassProduction.txt 6.24.html "./Greg_table_folder/6.24 Translation - Sheet1_merge.csv"

# python general_new.py all "./HTML_folder/6.25 ESP HTML/6.25 ESP HTML" 6-25_finalTemplate.brd 6-25_finalMassProduction.txt 6.25.html "./Greg_table_folder/6.25 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.25 ESP HTML/6.25 ESP HTML" GCF-mass.brd GCF-mass.txt 6.25.html "./Greg_table_folder/6.25 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.26 ESP HTML/6.26 ESP HTML" 6-26_finalTemplate-fixCBs.brd 6-26_finalMassProduction.txt 6.26.html "./Greg_table_folder/6.26 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.28 ESP HTML/6.28 ESP HTML" 6_28_start.brd 6_28_start.txt 6.28.html "./Greg_table_folder/6.28 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.30 ESP HTML/6.30 ESP HTML" masspro.brd masspro.txt 6.30.html "./Greg_table_folder/6.30 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/6.34 ESP HTML/6.34 ESP HTML" template_6.34_new.brd template_6.34.txt 6.34.html "./Greg_table_folder/6.34 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/8.17 ESP HTML/8.17 ESP HTML" finalTemplate.brd finalMassProdtable.txt 8.17.html "./Greg_table_folder/8.17 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/7.01 ESP HTML/7.01 ESP HTML" 7.01-mass.brd 7.01-mass.txt 7.01.html "./Greg_table_folder/7.01 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/7.02 ESP HTML/7.02 ESP HTML" 7_02_template.brd 7_02_template.txt 7.02.html "./Greg_table_folder/7.02 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/7.04 ESP HTML/7.04 ESP HTML" 7_04_finalTemplate.brd 7_04_finalMassProduction.txt 7.04.html "./Greg_table_folder/7.04 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/7.12 ESP HTML/7.12 ESP HTML" 7-12_finalTemplate.brd 7-12_finalMassProduction.txt 7.12.html "./Greg_table_folder/7.12 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/7.15 ESP HTML/7.15 ESP HTML" 7-15_finalTemplate.brd 7-15_finalMassProduction.txt 7.15.html "./Greg_table_folder/7.15 Translation - Sheet1.csv"

# python general_new.py all "./HTML_folder/7.16 ESP HTML/7.16 ESP HTML" 7-16_finalTemplate.brd 7-16_finalMassProduction.txt 7.16.html "./Greg_table_folder/7.16 - Sheet1.csv"

# python general_new.py all "./HTML_folder/8.05 ESP HTML/8.05 ESP HTML" 8-05tmpl.brd 8-05tmpl.txt 8.05.html "./Greg_table_folder/8.05 - Sheet1.csv"

# python general_new.py all "./HTML_folder/8.06 ESP HTML/8.06 ESP HTML" 8-06_finalTemplate.brd 8-06_finalMassProduction.txt 8.06.html "./Greg_table_folder/8.06 - Sheet1.csv"

# python general_new.py all "./HTML_folder/8.07 ESP HTML/8.07 ESP HTML" 8-07_finalTemplate.brd 8-07_finalMassProduction.txt 8.07.html "./Greg_table_folder/8.07 - Sheet1.csv"