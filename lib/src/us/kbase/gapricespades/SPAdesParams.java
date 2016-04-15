
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
 * string workspace_name - the name of the workspace from which to take input
 *    and store output.
 * paired_end_lib read_library_name - a PairedEndLibrary file to assemble.
 * bool single_cell - true if the reads are amplified data from a single
 *     cell (e.g. MDA data).
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "workspace_name",
    "read_library_name",
    "single_cell"
})
public class SPAdesParams {

    @JsonProperty("workspace_name")
    private String workspaceName;
    @JsonProperty("read_library_name")
    private String readLibraryName;
    @JsonProperty("single_cell")
    private Long singleCell;
    private Map<String, Object> additionalProperties = new HashMap<String, Object>();

    @JsonProperty("workspace_name")
    public String getWorkspaceName() {
        return workspaceName;
    }

    @JsonProperty("workspace_name")
    public void setWorkspaceName(String workspaceName) {
        this.workspaceName = workspaceName;
    }

    public SPAdesParams withWorkspaceName(String workspaceName) {
        this.workspaceName = workspaceName;
        return this;
    }

    @JsonProperty("read_library_name")
    public String getReadLibraryName() {
        return readLibraryName;
    }

    @JsonProperty("read_library_name")
    public void setReadLibraryName(String readLibraryName) {
        this.readLibraryName = readLibraryName;
    }

    public SPAdesParams withReadLibraryName(String readLibraryName) {
        this.readLibraryName = readLibraryName;
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
        return ((((((((("SPAdesParams"+" [workspaceName=")+ workspaceName)+", readLibraryName=")+ readLibraryName)+", singleCell=")+ singleCell)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
