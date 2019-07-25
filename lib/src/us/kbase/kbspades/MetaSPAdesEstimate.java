
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
 * <p>Original spec-file type: MetaSPAdesEstimate</p>
 * <pre>
 * cpus - the number of CPUs required for the run
 * memory - the minimal amount of memory in MB required for the run
 * walltime - an estimate for walltime in seconds for the run
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "cpus",
    "memory",
    "walltime"
})
public class MetaSPAdesEstimate {

    @JsonProperty("cpus")
    private Long cpus;
    @JsonProperty("memory")
    private Long memory;
    @JsonProperty("walltime")
    private Long walltime;
    private Map<String, Object> additionalProperties = new HashMap<String, Object>();

    @JsonProperty("cpus")
    public Long getCpus() {
        return cpus;
    }

    @JsonProperty("cpus")
    public void setCpus(Long cpus) {
        this.cpus = cpus;
    }

    public MetaSPAdesEstimate withCpus(Long cpus) {
        this.cpus = cpus;
        return this;
    }

    @JsonProperty("memory")
    public Long getMemory() {
        return memory;
    }

    @JsonProperty("memory")
    public void setMemory(Long memory) {
        this.memory = memory;
    }

    public MetaSPAdesEstimate withMemory(Long memory) {
        this.memory = memory;
        return this;
    }

    @JsonProperty("walltime")
    public Long getWalltime() {
        return walltime;
    }

    @JsonProperty("walltime")
    public void setWalltime(Long walltime) {
        this.walltime = walltime;
    }

    public MetaSPAdesEstimate withWalltime(Long walltime) {
        this.walltime = walltime;
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
        return ((((((((("MetaSPAdesEstimate"+" [cpus=")+ cpus)+", memory=")+ memory)+", walltime=")+ walltime)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
