
package us.kbase.kbunicycler;

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
 * <p>Original spec-file type: UnicyclerParams</p>
 * <pre>
 * To run Unicycler, you need at least one short read paired
 * end library, and optional unpaired reads (divided into short and
 * long.  All reads of the same time must be combined into a single
 * file.
 * workspace_name - the name of the workspace from which to take input
 *                  and store output.
 * output_contigset_name - the name of the output contigset
 * short_paired_libraries - a list of short, paired end reads libraries
 * short_unpaired_libraries - a list of short, paired end reads libraries
 * long_reads_libraries - a list of long reads
 * @optional min_contig_length
 * @optional num_linear_seqs
 * @optional bridging_mode
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "workspace_name",
    "output_contigset_name",
    "short_paired_libraries",
    "short_unpaired_libraries",
    "long_reads_library",
    "min_contig_length",
    "num_linear_seqs",
    "bridging_mode"
})
public class UnicyclerParams {

    @JsonProperty("workspace_name")
    private java.lang.String workspaceName;
    @JsonProperty("output_contigset_name")
    private java.lang.String outputContigsetName;
    @JsonProperty("short_paired_libraries")
    private List<String> shortPairedLibraries;
    @JsonProperty("short_unpaired_libraries")
    private List<String> shortUnpairedLibraries;
    @JsonProperty("long_reads_library")
    private java.lang.String longReadsLibrary;
    @JsonProperty("min_contig_length")
    private Long minContigLength;
    @JsonProperty("num_linear_seqs")
    private Long numLinearSeqs;
    @JsonProperty("bridging_mode")
    private java.lang.String bridgingMode;
    private Map<java.lang.String, Object> additionalProperties = new HashMap<java.lang.String, Object>();

    @JsonProperty("workspace_name")
    public java.lang.String getWorkspaceName() {
        return workspaceName;
    }

    @JsonProperty("workspace_name")
    public void setWorkspaceName(java.lang.String workspaceName) {
        this.workspaceName = workspaceName;
    }

    public UnicyclerParams withWorkspaceName(java.lang.String workspaceName) {
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

    public UnicyclerParams withOutputContigsetName(java.lang.String outputContigsetName) {
        this.outputContigsetName = outputContigsetName;
        return this;
    }

    @JsonProperty("short_paired_libraries")
    public List<String> getShortPairedLibraries() {
        return shortPairedLibraries;
    }

    @JsonProperty("short_paired_libraries")
    public void setShortPairedLibraries(List<String> shortPairedLibraries) {
        this.shortPairedLibraries = shortPairedLibraries;
    }

    public UnicyclerParams withShortPairedLibraries(List<String> shortPairedLibraries) {
        this.shortPairedLibraries = shortPairedLibraries;
        return this;
    }

    @JsonProperty("short_unpaired_libraries")
    public List<String> getShortUnpairedLibraries() {
        return shortUnpairedLibraries;
    }

    @JsonProperty("short_unpaired_libraries")
    public void setShortUnpairedLibraries(List<String> shortUnpairedLibraries) {
        this.shortUnpairedLibraries = shortUnpairedLibraries;
    }

    public UnicyclerParams withShortUnpairedLibraries(List<String> shortUnpairedLibraries) {
        this.shortUnpairedLibraries = shortUnpairedLibraries;
        return this;
    }

    @JsonProperty("long_reads_library")
    public java.lang.String getLongReadsLibrary() {
        return longReadsLibrary;
    }

    @JsonProperty("long_reads_library")
    public void setLongReadsLibrary(java.lang.String longReadsLibrary) {
        this.longReadsLibrary = longReadsLibrary;
    }

    public UnicyclerParams withLongReadsLibrary(java.lang.String longReadsLibrary) {
        this.longReadsLibrary = longReadsLibrary;
        return this;
    }

    @JsonProperty("min_contig_length")
    public Long getMinContigLength() {
        return minContigLength;
    }

    @JsonProperty("min_contig_length")
    public void setMinContigLength(Long minContigLength) {
        this.minContigLength = minContigLength;
    }

    public UnicyclerParams withMinContigLength(Long minContigLength) {
        this.minContigLength = minContigLength;
        return this;
    }

    @JsonProperty("num_linear_seqs")
    public Long getNumLinearSeqs() {
        return numLinearSeqs;
    }

    @JsonProperty("num_linear_seqs")
    public void setNumLinearSeqs(Long numLinearSeqs) {
        this.numLinearSeqs = numLinearSeqs;
    }

    public UnicyclerParams withNumLinearSeqs(Long numLinearSeqs) {
        this.numLinearSeqs = numLinearSeqs;
        return this;
    }

    @JsonProperty("bridging_mode")
    public java.lang.String getBridgingMode() {
        return bridgingMode;
    }

    @JsonProperty("bridging_mode")
    public void setBridgingMode(java.lang.String bridgingMode) {
        this.bridgingMode = bridgingMode;
    }

    public UnicyclerParams withBridgingMode(java.lang.String bridgingMode) {
        this.bridgingMode = bridgingMode;
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
        return ((((((((((((((((((("UnicyclerParams"+" [workspaceName=")+ workspaceName)+", outputContigsetName=")+ outputContigsetName)+", shortPairedLibraries=")+ shortPairedLibraries)+", shortUnpairedLibraries=")+ shortUnpairedLibraries)+", longReadsLibrary=")+ longReadsLibrary)+", minContigLength=")+ minContigLength)+", numLinearSeqs=")+ numLinearSeqs)+", bridgingMode=")+ bridgingMode)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
