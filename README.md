# Python Interface Package for Nanonis 

Official python package for the Nanonis SPM Controller software.

## Usage

This package allows users of the Nanonis SPM Controller software to use and control
said software through python commands.

## How to use

### Importing

import nanonis_spm

### Initializing Connection through the socket module

import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

connection.connect((IP_ADRESS_HERE, PORT_HERE))

nanonisInstance = nanonis_spm.Nanonis(connection)

NOTE : THE PORT HAS TO BE AN INTEGER AND THE IP ADRESS A STRING

### Enabling Debug Console Output

The function "returnDebugInfo()" takes an integer as an argument. 
This integer should be either 1 = on, or 0 = off. This option is off by default.

Enable by running:
nanonisInstance.returnDebugInfo(1)

### Examples

There is a collection of examples installed with the package.

The description of all the available functions can be found in the TCP Protocol Document, and hovering on the function depending on the used IDE.

IMPORTANT:
The TCP Interface requires every argument to be of certain size (see documentation).
This is why the Numpy dependency is required, since it enables the specification
of variable sizes. 

Example:

nanonisInstance.BiasSwp_LimitsSet(np.float32(1), np.float32(2))

We hereby ensure that the arguments are of the correct size.


