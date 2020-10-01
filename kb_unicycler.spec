/*
A KBase module: kb_unicycler
A wrapper for the unicycler assembler
*/

module kb_unicycler {

    /* The workspace object name of a PairedEndLibrary file, whether of the
       KBaseAssembly or KBaseFile type.
    */
    typedef string paired_lib;

    /* The workspace object name of a SingleEndLibrary file, whether of the
       KBaseAssembly or KBaseFile type.
    */
    typedef string unpaired_lib;

    /*
    To run Unicycler, you need at least one short read paired
    end library, and optional unpaired reads (divided into short and
    long.  All reads of the same time must be combined into a single
    file.

    workspace_name - the name of the workspace from which to take input
                     and store output.
    output_contigset_name - the name of the output contigset
    short_paired_libraries - a list of short, paired end reads libraries
    short_unpaired_libraries - a list of short, paired end reads libraries
    long_reads_libraries - a list of long reads

    @optional min_contig_length
    @optional num_linear_seqs
    @optional bridging_mode
    */

    typedef structure {
        string workspace_name;
        string output_contigset_name;
        list<paired_lib> short_paired_libraries;
        list<unpaired_lib> short_unpaired_libraries;
        list<unpaired_lib> long_reads_libraries;

        int min_contig_length;
        int num_linear_seqs;
        string bridging_mode;
    } UnicyclerParams;

    /* Output parameters for Unicycler run.
    report_name - the name of the KBaseReport.Report workspace object.
    report_ref - the workspace reference of the report.
    */
    typedef structure {
        string report_name;
        string report_ref;
    } UnicyclerOutput;
    
    /* Run Unicycler */
    funcdef run_unicycler(UnicyclerParams params) returns(UnicyclerOutput output)
        authentication required;
};

