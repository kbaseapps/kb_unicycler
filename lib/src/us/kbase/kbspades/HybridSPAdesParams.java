
package us.kbase.kbspades;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.annotation.Generated;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * <p>Original spec-file type: HybridSPAdesParams</p>
 * <pre>
 * ------To run SPAdes 3.13.0 you need at least one library of the following types:------
 *  1) Illumina paired-end/high-quality mate-pairs/unpaired reads
 *  2) IonTorrent paired-end/high-quality mate-pairs/unpaired reads
 *  3) PacBio CCS reads
 * workspace_name - the name of the workspace from which to take input
 *                  and store output.
 * output_contigset_name - the name of the output contigset
 * single_reads - a list of Illumina/IonTorrent single reads or unpaired reads from paired library
 * pairedEnd_reads - a list of Illumina/IonTorrent PairedEndLibrary reads
 * mate_pair_reads - a list of Illumina/IonTorrent Mate Pair or unpaired reads
 * pacbio_reads - a list of PacBio CLR reads 
 * nanopore_reads - a list of Oxford Nanopore reads
 * dna_source - the source of the DNA used for sequencing 'single_cell': DNA
 *                  amplified from a single cell via MDA anything else: Standard
 *                  DNA sample from multiple cells. Default value is None.
 * min_contig_length - an integer to filter out contigs with length < min_contig_length
 *                  from the SPAdes output. Default value is 0 implying no filter.
 * kmer_sizes - K-mer sizes, Default values: 33, 55, 77, 99, 127
 *                  (all values must be odd, less than 128 and listed in ascending order)
 *                  In the absence of these values, K values are automatically selected.
 * skip_error_correction - Assembly only (No error correction).
 *                  By default this is disabled.
 * @optional pacbio_reads
 * @optional nanopore_reads
 * @optional dna_source
 * @optional min_contig_length
 * @optional kmer_sizes
 * @optional skip_error_correction
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "workspace_name",
    "output_contigset_name",
    "single_reads",
    "pairedEnd_reads",
    "mate_pair_reads",
    "pacbio_reads",
    "nanopore_reads",
    "dna_source",
    "min_contig_length",
    "kmer_sizes",
    "skip_error_correction"
})
public class HybridSPAdesParams {

    @JsonProperty("workspace_name")
    private String workspaceName;
    @JsonProperty("output_contigset_name")
    private String outputContigsetName;
    @JsonProperty("single_reads")
    private List<us.kbase.kbspades.ReadsParams> singleReads;
    @JsonProperty("pairedEnd_reads")
    private List<us.kbase.kbspades.ReadsParams> pairedEndReads;
    @JsonProperty("mate_pair_reads")
    private List<us.kbase.kbspades.ReadsParams> matePairReads;
    @JsonProperty("pacbio_reads")
    private List<us.kbase.kbspades.ReadsParams> pacbioReads;
    @JsonProperty("nanopore_reads")
    private List<us.kbase.kbspades.ReadsParams> nanoporeReads;
    @JsonProperty("dna_source")
    private String dnaSource;
    @JsonProperty("min_contig_length")
    private java.lang.Long minContigLength;
    @JsonProperty("kmer_sizes")
    private List<Long> kmerSizes;
    @JsonProperty("skip_error_correction")
    private java.lang.Long skipErrorCorrection;
    private Map<String, Object> additionalProperties = new HashMap<String, Object>();

    @JsonProperty("workspace_name")
    public String getWorkspaceName() {
        return workspaceName;
    }

    @JsonProperty("workspace_name")
    public void setWorkspaceName(String workspaceName) {
        this.workspaceName = workspaceName;
    }

    public HybridSPAdesParams withWorkspaceName(String workspaceName) {
        this.workspaceName = workspaceName;
        return this;
    }

    @JsonProperty("output_contigset_name")
    public String getOutputContigsetName() {
        return outputContigsetName;
    }

    @JsonProperty("output_contigset_name")
    public void setOutputContigsetName(String outputContigsetName) {
        this.outputContigsetName = outputContigsetName;
    }

    public HybridSPAdesParams withOutputContigsetName(String outputContigsetName) {
        this.outputContigsetName = outputContigsetName;
        return this;
    }

    @JsonProperty("single_reads")
    public List<us.kbase.kbspades.ReadsParams> getSingleReads() {
        return singleReads;
    }

    @JsonProperty("single_reads")
    public void setSingleReads(List<us.kbase.kbspades.ReadsParams> singleReads) {
        this.singleReads = singleReads;
    }

    public HybridSPAdesParams withSingleReads(List<us.kbase.kbspades.ReadsParams> singleReads) {
        this.singleReads = singleReads;
        return this;
    }

    @JsonProperty("pairedEnd_reads")
    public List<us.kbase.kbspades.ReadsParams> getPairedEndReads() {
        return pairedEndReads;
    }

    @JsonProperty("pairedEnd_reads")
    public void setPairedEndReads(List<us.kbase.kbspades.ReadsParams> pairedEndReads) {
        this.pairedEndReads = pairedEndReads;
    }

    public HybridSPAdesParams withPairedEndReads(List<us.kbase.kbspades.ReadsParams> pairedEndReads) {
        this.pairedEndReads = pairedEndReads;
        return this;
    }

    @JsonProperty("mate_pair_reads")
    public List<us.kbase.kbspades.ReadsParams> getMatePairReads() {
        return matePairReads;
    }

    @JsonProperty("mate_pair_reads")
    public void setMatePairReads(List<us.kbase.kbspades.ReadsParams> matePairReads) {
        this.matePairReads = matePairReads;
    }

    public HybridSPAdesParams withMatePairReads(List<us.kbase.kbspades.ReadsParams> matePairReads) {
        this.matePairReads = matePairReads;
        return this;
    }

    @JsonProperty("pacbio_reads")
    public List<us.kbase.kbspades.ReadsParams> getPacbioReads() {
        return pacbioReads;
    }

    @JsonProperty("pacbio_reads")
    public void setPacbioReads(List<us.kbase.kbspades.ReadsParams> pacbioReads) {
        this.pacbioReads = pacbioReads;
    }

    public HybridSPAdesParams withPacbioReads(List<us.kbase.kbspades.ReadsParams> pacbioReads) {
        this.pacbioReads = pacbioReads;
        return this;
    }

    @JsonProperty("nanopore_reads")
    public List<us.kbase.kbspades.ReadsParams> getNanoporeReads() {
        return nanoporeReads;
    }

    @JsonProperty("nanopore_reads")
    public void setNanoporeReads(List<us.kbase.kbspades.ReadsParams> nanoporeReads) {
        this.nanoporeReads = nanoporeReads;
    }

    public HybridSPAdesParams withNanoporeReads(List<us.kbase.kbspades.ReadsParams> nanoporeReads) {
        this.nanoporeReads = nanoporeReads;
        return this;
    }

    @JsonProperty("dna_source")
    public String getDnaSource() {
        return dnaSource;
    }

    @JsonProperty("dna_source")
    public void setDnaSource(String dnaSource) {
        this.dnaSource = dnaSource;
    }

    public HybridSPAdesParams withDnaSource(String dnaSource) {
        this.dnaSource = dnaSource;
        return this;
    }

    @JsonProperty("min_contig_length")
    public java.lang.Long getMinContigLength() {
        return minContigLength;
    }

    @JsonProperty("min_contig_length")
    public void setMinContigLength(java.lang.Long minContigLength) {
        this.minContigLength = minContigLength;
    }

    public HybridSPAdesParams withMinContigLength(java.lang.Long minContigLength) {
        this.minContigLength = minContigLength;
        return this;
    }

    @JsonProperty("kmer_sizes")
    public List<Long> getKmerSizes() {
        return kmerSizes;
    }

    @JsonProperty("kmer_sizes")
    public void setKmerSizes(List<Long> kmerSizes) {
        this.kmerSizes = kmerSizes;
    }

    public HybridSPAdesParams withKmerSizes(List<Long> kmerSizes) {
        this.kmerSizes = kmerSizes;
        return this;
    }

    @JsonProperty("skip_error_correction")
    public java.lang.Long getSkipErrorCorrection() {
        return skipErrorCorrection;
    }

    @JsonProperty("skip_error_correction")
    public void setSkipErrorCorrection(java.lang.Long skipErrorCorrection) {
        this.skipErrorCorrection = skipErrorCorrection;
    }

    public HybridSPAdesParams withSkipErrorCorrection(java.lang.Long skipErrorCorrection) {
        this.skipErrorCorrection = skipErrorCorrection;
        return this;
    }

    @JsonAnyGetter
    public Map<String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public String toString() {
        return ((((((((((((((((((((((((("HybridSPAdesParams"+" [workspaceName=")+ workspaceName)+", outputContigsetName=")+ outputContigsetName)+", singleReads=")+ singleReads)+", pairedEndReads=")+ pairedEndReads)+", matePairReads=")+ matePairReads)+", pacbioReads=")+ pacbioReads)+", nanoporeReads=")+ nanoporeReads)+", dnaSource=")+ dnaSource)+", minContigLength=")+ minContigLength)+", kmerSizes=")+ kmerSizes)+", skipErrorCorrection=")+ skipErrorCorrection)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
