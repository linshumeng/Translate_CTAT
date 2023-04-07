# Translate_CTAT

## Purpose

The purpose of this script is to automatically translate an entire package from English to another language, such as Spanish. The process involves several steps, which include:

- clean: extract all the sentences(not variables, e.g. hints) from the massproduction graph(.brd) to ensure the translation only occurs on the massproduction table(.txt).

- mass_produce: the purpose of the whole script is to provide an end-to-end way of translation, so mass_produce here can to achieve the function in CTAT -- mass-produce .brds.

- validate: this function provides a direct result indicating whether the .brd file generated from the script matches the one generated from CTAT.

- translate: there are three files that require translation: the mass production table, HTML, and package.xml.

## Achievement

- clean: in the clean part of the script, there are several tasks that need to be achieved:
  - Assigning new variable names to sentences: The convention followed is "tag+count+first4word" to generate a unique variable name for each sentence.
  - Identifying and renaming hash-like variables: Hash-like variables found in the massproduction graph should be assigned new variable names.
  - Modifying both the massproduction graph and the massproduction table to reflect the changes made.
- mass_produce: in the mass_produce part of the script, there are several tasks that need to be achieved:
  - Changing format into XML format, such as <% to &lt:%: This includes converting special characters such as '<%' to their corresponding XML entities, such as '&lt;%' to ensure compliance with XML formatting requirements.
  - Replacing variables in the massproduction graph with their corresponding values in the massproduction table.

## Arguments

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
