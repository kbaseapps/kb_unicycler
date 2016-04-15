
package us.kbase.gapricespades;

import java.util.HashMap;
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
 * paired_end_lib library - a PairedEndLibrary file to assemble.
 * bool single_cell - true if the reads are amplified data from a single
 *     cell (e.g. MDA data).
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "workspace",
    "library",
    "single_cell"
})
public class SPAdesParams {

    @JsonProperty("workspace")
    private String workspace;
    @JsonProperty("library")
    private String library;
    @JsonProperty("single_cell")
    private Long singleCell;
    private Map<String, Object> additionalProperties = new HashMap<String, Object>();

    @JsonProperty("workspace")
    public String getWorkspace() {
        return workspace;
    }

    @JsonProperty("workspace")
    public void setWorkspace(String workspace) {
        this.workspace = workspace;
    }

    public SPAdesParams withWorkspace(String workspace) {
        this.workspace = workspace;
        return this;
    }

    @JsonProperty("library")
    public String getLibrary() {
        return library;
    }

    @JsonProperty("library")
    public void setLibrary(String library) {
        this.library = library;
    }

    public SPAdesParams withLibrary(String library) {
        this.library = library;
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
    public Map<String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public String toString() {
        return ((((((((("SPAdesParams"+" [workspace=")+ workspace)+", library=")+ library)+", singleCell=")+ singleCell)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
