
package us.kbase.gapricespades;

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
 * <p>Original spec-file type: SPAdesParams</p>
 * <pre>
 * Input parameters for running SPAdes.
 * string workspace - the name of the workspace from which to take input
 *    and store output.
 * list<paired_end_lib> libraries - a list of PairedEndLibrary files to
 *     assemble. Currently assembling up to 9 files at once is supported.
 * bool single_cell - true if the reads are amplified data from a single
 *     cell (e.g. MDA data).
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "workspace",
    "libraries",
    "single_cell"
})
public class SPAdesParams {

    @JsonProperty("workspace")
    private java.lang.String workspace;
    @JsonProperty("libraries")
    private List<String> libraries;
    @JsonProperty("single_cell")
    private Long singleCell;
    private Map<java.lang.String, Object> additionalProperties = new HashMap<java.lang.String, Object>();

    @JsonProperty("workspace")
    public java.lang.String getWorkspace() {
        return workspace;
    }

    @JsonProperty("workspace")
    public void setWorkspace(java.lang.String workspace) {
        this.workspace = workspace;
    }

    public SPAdesParams withWorkspace(java.lang.String workspace) {
        this.workspace = workspace;
        return this;
    }

    @JsonProperty("libraries")
    public List<String> getLibraries() {
        return libraries;
    }

    @JsonProperty("libraries")
    public void setLibraries(List<String> libraries) {
        this.libraries = libraries;
    }

    public SPAdesParams withLibraries(List<String> libraries) {
        this.libraries = libraries;
        return this;
    }

    @JsonProperty("single_cell")
    public Long getSingleCell() {
        return singleCell;
    }

    @JsonProperty("single_cell")
    public void setSingleCell(Long singleCell) {
        this.singleCell = singleCell;
    }

    public SPAdesParams withSingleCell(Long singleCell) {
        this.singleCell = singleCell;
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
        return ((((((((("SPAdesParams"+" [workspace=")+ workspace)+", libraries=")+ libraries)+", singleCell=")+ singleCell)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
