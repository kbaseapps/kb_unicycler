/*
A KBase module: gaprice_SPAdes
Simple wrapper for the SPAdes assembler.
http://bioinf.spbau.ru/spades

Currently only supports assembling one PairedEndLibrary at a time.
Always runs in careful mode.
Runs 3 threads / CPU.
Maximum memory use is set to available memory - 1G.
Autodetection is used for the PHRED quality offset and k-mer sizes.
A coverage cutoff is not specified.
Does not currently support assembling metagenomics reads.

*/

module gaprice_SPAdes {

    /* A boolean. 0 = false, anything else = true. */
    typedef int bool;
    
    /* The workspace object name of a PairedEndLibrary file, whether of the
       KBaseAssembly or KBaseFile type.
    */
    typedef string paired_end_lib;
    
    /* Input parameters for running SPAdes.
        string workspace_name - the name of the workspace from which to take input
           and store output.
        paired_end_lib read_library_name - a PairedEndLibrary file to assemble.
        bool single_cell - true if the reads are amplified data from a single
            cell (e.g. MDA data).
    */
    typedef structure {
        string workspace_name;
        paired_end_lib read_library_name;
        bool single_cell;
    } SPAdesParams;
    
    /* Output parameters for SPAdes run.
        string report_name - the name of the KBaseReport.Report workspace
            object.
        string report_ref - the workspace reference of the report.
    */
    typedef structure {
        string report_name;
        string report_ref;
    } SPAdesOutput;
    
    /* Run SPAdes on paired end libraries */
    funcdef run_SPAdes(SPAdesParams params) returns(SPAdesOutput output)
        authentication required;
};