
package us.kbase.kbspades;

import java.util.HashMap;
import java.util.Map;
import javax.annotation.Generated;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * <p>Original spec-file type: MetaSPAdesEstimatorParams</p>
 * <pre>
 * params - the params used to run metaSPAdes.
 * use_defaults - (optional, def 0) if 1, just return the default requirements
 * use_heuristic - (optional, def 1) if 1, only use a heuristic based on the reads metadata to perform estimates
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "params",
    "use_defaults"
})
public class MetaSPAdesEstimatorParams {

    /**
     * <p>Original spec-file type: SPAdesParams</p>
     * <pre>
     * Input parameters for running SPAdes.
     * workspace_name - the name of the workspace from which to take input
     *                  and store output.
     * output_contigset_name - the name of the output contigset
     * read_libraries - a list of Illumina PairedEndLibrary files in FASTQ or BAM format.
     * dna_source - (optional) the source of the DNA used for sequencing 'single_cell': DNA
     *                  amplified from a single cell via MDA anything else: Standard
     *                  DNA sample from multiple cells. Default value is None.
     * min_contig_length - (optional) integer to filter out contigs with length < min_contig_length
     *                  from the SPAdes output. Default value is 0 implying no filter.
     * kmer_sizes - (optional) K-mer sizes, Default values: 33, 55, 77, 99, 127
     *                  (all values must be odd, less than 128 and listed in ascending order)
     *                  In the absence of these values, K values are automatically selected.
     * skip_error_correction - (optional) Assembly only (No error correction).
     *                  By default this is disabled.
     * </pre>
     * 
     */
    @JsonProperty("params")
    private SPAdesParams params;
    @JsonProperty("use_defaults")
    private Long useDefaults;
    private Map<String, Object> additionalProperties = new HashMap<String, Object>();

    /**
     * <p>Original spec-file type: SPAdesParams</p>
     * <pre>
     * Input parameters for running SPAdes.
     * workspace_name - the name of the workspace from which to take input
     *                  and store output.
     * output_contigset_name - the name of the output contigset
     * read_libraries - a list of Illumina PairedEndLibrary files in FASTQ or BAM format.
     * dna_source - (optional) the source of the DNA used for sequencing 'single_cell': DNA
     *                  amplified from a single cell via MDA anything else: Standard
     *                  DNA sample from multiple cells. Default value is None.
     * min_contig_length - (optional) integer to filter out contigs with length < min_contig_length
     *                  from the SPAdes output. Default value is 0 implying no filter.
     * kmer_sizes - (optional) K-mer sizes, Default values: 33, 55, 77, 99, 127
     *                  (all values must be odd, less than 128 and listed in ascending order)
     *                  In the absence of these values, K values are automatically selected.
     * skip_error_correction - (optional) Assembly only (No error correction).
     *                  By default this is disabled.
     * </pre>
     * 
     */
    @JsonProperty("params")
    public SPAdesParams getParams() {
        return params;
    }

    /**
     * <p>Original spec-file type: SPAdesParams</p>
     * <pre>
     * Input parameters for running SPAdes.
     * workspace_name - the name of the workspace from which to take input
     *                  and store output.
     * output_contigset_name - the name of the output contigset
     * read_libraries - a list of Illumina PairedEndLibrary files in FASTQ or BAM format.
     * dna_source - (optional) the source of the DNA used for sequencing 'single_cell': DNA
     *                  amplified from a single cell via MDA anything else: Standard
     *                  DNA sample from multiple cells. Default value is None.
     * min_contig_length - (optional) integer to filter out contigs with length < min_contig_length
     *                  from the SPAdes output. Default value is 0 implying no filter.
     * kmer_sizes - (optional) K-mer sizes, Default values: 33, 55, 77, 99, 127
     *                  (all values must be odd, less than 128 and listed in ascending order)
     *                  In the absence of these values, K values are automatically selected.
     * skip_error_correction - (optional) Assembly only (No error correction).
     *                  By default this is disabled.
     * </pre>
     * 
     */
    @JsonProperty("params")
    public void setParams(SPAdesParams params) {
        this.params = params;
    }

    public MetaSPAdesEstimatorParams withParams(SPAdesParams params) {
        this.params = params;
        return this;
    }

    @JsonProperty("use_defaults")
    public Long getUseDefaults() {
        return useDefaults;
    }

    @JsonProperty("use_defaults")
    public void setUseDefaults(Long useDefaults) {
        this.useDefaults = useDefaults;
    }

    public MetaSPAdesEstimatorParams withUseDefaults(Long useDefaults) {
        this.useDefaults = useDefaults;
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
        return ((((((("MetaSPAdesEstimatorParams"+" [params=")+ params)+", useDefaults=")+ useDefaults)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
