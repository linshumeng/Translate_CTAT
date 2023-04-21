# Translate_CTAT

## What is CTAT?

The [Cognitive Tutor Authoring Tools (CTAT)](https://github.com/CMUCTAT/CTAT), is a tool suite that enables you to add learning by doing (i.e., active learning) to online courses. It is developed by Carnegie Mellon University.

## Purpose of this script

The purpose of this script is to automatically translate an entire CTAT package from English to another language, such as Spanish. The process involves several steps, which include:

- clean: extract all the sentences(not variables, e.g. hints) from the massproduction graph(.brd) to ensure the translation only occurs on the massproduction table(.txt).

- mass_produce: the purpose of the whole script is to provide an end-to-end way of translation, so mass_produce here can to achieve the function in CTAT -- mass-produce .brds.

- validate: this function provides a direct result indicating whether the .brd file generated from the script matches the one generated from CTAT.

- translate: there are three files that require translation: the mass production table, HTML, and package.xml.

## Achievement

- clean
  - Assigning new variable names to sentences: The convention followed is "tag+count+first4word" to generate a unique variable name for each sentence.
  - Identifying and renaming hash-like variables: Hash-like variables found in the massproduction graph should be assigned new variable names.
  - Modifying both the massproduction graph and the massproduction table to reflect the changes made.
  - Output: by default, a new txt named \_cleaned.txt will be created under MassProduction.
  - Output: by default, a new brd named \_cleaned.brd will be created under MassProduction.
- mass_produce
  - Changing format into XML format, such as <% to &lt:%: This includes converting special characters such as '<%' to their corresponding XML entities, such as '&lt;%' to ensure compliance with XML formatting requirements.
  - Replacing variables in the massproduction graph with their corresponding values in the massproduction table.
  - Output: by default, a new folder named CleanedBRDs will be created under FinalBRDs.
- validate
  - Comparing two brds using two packages.
- translate massproduction table
  - Protecting variable names during translation: Some variable names, such as %(startStateNodeName)% or graphic items that indicate paths of graphs, need to be protected and should not be translated.
  - Applying rules to avoid translation of certain strings: For example, formulas and numeric values may not need to be translated directly.
  - Utilizing a reference table: A reference table can be imported to avoid making calls to external translation APIs. If a reference table exists, it should be prioritized for translation, and only strings not found in the table should be translated using other translation APIs.
  - Output: by default, a new txt named \_translated.txt will be created under MassProduction.
  - Output: by default, a new txt named \_translated[marked].brd will be created under MassProduction, which indicates will field is translated by google.
- translate brd
  - It follows a similar logic as the translation of the massproduction table. The script takes an input folder containing brd files and iterates through them, translating specific tags as required. The script can also accept a reference table as input to improve the quality of translation.
- translate HTML
  - Output: by default, a new html named \_es.html will be created under HTML.
- translate XML
  - Utilizing a reference table or calling Google API for translation: Similar to the translation of the massproduction table, a reference table can be used to avoid making unnecessary calls to external translation APIs. If a reference table is not available, other translation APIs, such as Google Translate API, can be called to translate the XML content.
  - Modifying certain attributes: The script should modify specific attributes in the XML file, including "label", "category", "description", "model_file", and "student_interface". The "label" and "category" attributes should only have an ISO code(\_es) added, while the "description" attribute should be translated but limited to a maximum length of 255 characters. The "model_file" and "student_interface" attributes should be updated to correspond with the newly generated files after translation.
  - Output: by default, the old one will be renamed as package_en.xml and the new one will be named as package.xml.

## Arguments

Currently, the script can be called from the command-line with basic functionality that performs all the steps(clean, translate, mass_produce and validate). Users can input the paths of the original massproduction table and graph, and the script will compute the paths of other intermediate files or users can indicate the paths. Users also have the option to pass in a reference table for translation.

Here's an example command line call for the script using the provided arguments:

`python general_new.py all "./HTML_folder/7.06 ESP HTML/7.06 ESP HTML" 7_06.brd 7_06.txt 7.06.html "./Greg_table_folder/7.06 - Sheet1.csv"`

If users want to translate single brd, the input arguments will be:

`python general_new.py single "./HTML_folder/7.54 ESP HTML/7.54 ESP HTML" "7.54.html" "./Greg_table_folder/7.54 - Sheet1.csv"`

## Requirements(packages)

- os: For interacting with the operating system, such as file and directory operations.
- sys: For interacting with the Python runtime environment, such as system-related operations.
- tqdm: For adding progress bars to loops and other iterable objects.
- glob: For finding all the pathnames matching a specified pattern according to the rules used by the Unix shell.
- pandas: For data manipulation, working in tabular format.
- re: For regular expressions, used for pattern matching and string manipulation.
- nltk.corpus.stopwords: For accessing a list of stop words in natural language processing.
- translators.server: For translation services.
- xml.etree.ElementTree: For parsing and manipulating XML data.
- lxml.html: For parsing and manipulating HTML data.
- xmldiff.main: For comparing and diffing XML documents.

## Known bugs

The script is not completely bug-free and there are several known issues that need to be addressed:

- Ampersand character: In XML, the ampersand character (&) should be treated as &amp; to comply with the XML syntax rules. This issue has not been addressed in the current version of the script.
- Quotation marks and periods: After translation, the order of quotation marks and periods may change.
- Translation of function parameters: Some function parameters that indicate the state of the function, such as "hidden", "true", and "false", may also be translated.
- Translation of brds instead of the massproduction table: If brds are translated instead of the massproduction table, certain fields such as <matcherParameter> may not be translated.
