
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
 * pipeline_options - a list of string specifying how the SPAdes pipeline should be run
 * @optional pacbio_reads
 * @optional nanopore_reads
 * @optional dna_source
 * @optional pipeline_options
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
    "pipeline_options",
    "create_report"
})
public class HybridSPAdesParams {

    @JsonProperty("workspace_name")
    private java.lang.String workspaceName;
    @JsonProperty("output_contigset_name")
    private java.lang.String outputContigsetName;
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
    private java.lang.String dnaSource;
    @JsonProperty("pipeline_options")
    private List<String> pipelineOptions;
    @JsonProperty("create_report")
    private Long createReport;
    private Map<java.lang.String, Object> additionalProperties = new HashMap<java.lang.String, Object>();

    @JsonProperty("workspace_name")
    public java.lang.String getWorkspaceName() {
        return workspaceName;
    }

    @JsonProperty("workspace_name")
    public void setWorkspaceName(java.lang.String workspaceName) {
        this.workspaceName = workspaceName;
    }

    public HybridSPAdesParams withWorkspaceName(java.lang.String workspaceName) {
        this.workspaceName = workspaceName;
        return this;
    }

    @JsonProperty("output_contigset_name")
    public java.lang.String getOutputContigsetName() {
        return outputContigsetName;
    }

    @JsonProperty("output_contigset_name")
    public void setOutputContigsetName(java.lang.String outputContigsetName) {
        this.outputContigsetName = outputContigsetName;
    }

    public HybridSPAdesParams withOutputContigsetName(java.lang.String outputContigsetName) {
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
    public java.lang.String getDnaSource() {
        return dnaSource;
    }

    @JsonProperty("dna_source")
    public void setDnaSource(java.lang.String dnaSource) {
        this.dnaSource = dnaSource;
    }

    public HybridSPAdesParams withDnaSource(java.lang.String dnaSource) {
        this.dnaSource = dnaSource;
        return this;
    }

    @JsonProperty("pipeline_options")
    public List<String> getPipelineOptions() {
        return pipelineOptions;
    }

    @JsonProperty("pipeline_options")
    public void setPipelineOptions(List<String> pipelineOptions) {
        this.pipelineOptions = pipelineOptions;
    }

    public HybridSPAdesParams withPipelineOptions(List<String> pipelineOptions) {
        this.pipelineOptions = pipelineOptions;
        return this;
    }

    @JsonProperty("create_report")
    public Long getCreateReport() {
        return createReport;
    }

    @JsonProperty("create_report")
    public void setCreateReport(Long createReport) {
        this.createReport = createReport;
    }

    public HybridSPAdesParams withCreateReport(Long createReport) {
        this.createReport = createReport;
        return this;
    }

    @JsonAnyGetter
    public Map<java.lang.String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(java.lang.String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public java.lang.String toString() {
        return ((((((((((((((((((((((("HybridSPAdesParams"+" [workspaceName=")+ workspaceName)+", outputContigsetName=")+ outputContigsetName)+", singleReads=")+ singleReads)+", pairedEndReads=")+ pairedEndReads)+", matePairReads=")+ matePairReads)+", pacbioReads=")+ pacbioReads)+", nanoporeReads=")+ nanoporeReads)+", dnaSource=")+ dnaSource)+", pipelineOptions=")+ pipelineOptions)+", createReport=")+ createReport)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
