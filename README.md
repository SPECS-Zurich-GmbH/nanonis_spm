# Python Interface Package for Nanonis 

Official python package for the Nanonis SPM Controller software.

## Usage

This package allows users of the Nanonis SPM Controller software to use and control
said software through python commands.

## How to use

### Importing

import nanonis_spm

### Initializing Connection

nanonisInstance = nanonis_spm.Nanonis(PORT_HERE, IP_ADRESS_HERE)

NOTE : THE PORT HAS TO BE AN INTEGER AND THE IP ADRESS A STRING

### Enabling Debug Console Output

The function "returnDebugInfo()" takes an integer as an argument. 
This integer should be either 1 = on, or 0 = off. This option is off by default.

Enable by running:
nanonisInstance.returnDebugInfo(1)

### Examples

nanonisInstance.BiasSpectr_Open() --> Opens Bias Spectroscopy Module.

Funtion Documentations can be found by either hovering over the function names
or in the TCP Protocol Document, which is also where all the available functions
are listed.x

IMPORTANT:
The TCP Interface requires every argument to be of certain size (see documentation).
This is why the Numpy dependency is required, since it enables the specification
of variable sizes. 

Example:

nanonisInstance.BiasSwp_LimitsSet(np.float32(1), np.float32(2))

We hereby ensure that the arguments are of the correct size.
Strings are to be input normally as such:

nanonisInstance.HSSwp_SaveBasenameSet("test")



