# Tooling reference

Contents: Maven verbose output, Gradle insight output, BOM syntax, Enforcer configuration, shading checks.

## Maven

```bash
mvn dependency:tree -Dverbose -Dincludes=groupId:artifactId
mvn help:effective-pom -Doutput=/tmp/effective-pom.xml
```

Verbose output lists omitted nodes with a reason such as "omitted for duplicate" or "omitted for conflict with 2.9.0". `help:effective-pom` shows the resolved `dependencyManagement`, including what a parent or an imported BOM contributed. Maven uses the nearest definition in the tree, and the first declared wins on a tie, so reordering declarations changes the result.

Import a BOM:

```xml
<dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>com.fasterxml.jackson</groupId>
      <artifactId>jackson-bom</artifactId>
      <version>2.17.2</version>
      <type>pom</type>
      <scope>import</scope>
    </dependency>
  </dependencies>
</dependencyManagement>
```

When a Spring Boot parent is in use, its managed versions apply; overriding a single managed library is done with the version property the parent defines, not by repeating the dependency.

## Gradle

```bash
gradle dependencyInsight --dependency jackson-databind --configuration runtimeClasspath
gradle dependencies --configuration runtimeClasspath
```

Insight prints each requested version, the selected one and the reason. Gradle picks the highest requested version unless a constraint, a platform or a strict version says otherwise. Use a platform:

```kotlin
dependencies {
    implementation(platform("com.fasterxml.jackson:jackson-bom:2.17.2"))
    implementation("com.fasterxml.jackson.core:jackson-databind")
}
```

Fail on conflicts:

```kotlin
configurations.all {
    resolutionStrategy { failOnVersionConflict() }
}
```

## Maven Enforcer

```xml
<plugin>
  <artifactId>maven-enforcer-plugin</artifactId>
  <executions>
    <execution>
      <id>enforce</id>
      <goals><goal>enforce</goal></goals>
      <configuration>
        <rules>
          <dependencyConvergence/>
          <banDuplicateClasses>
            <findAllDuplicates>true</findAllDuplicates>
          </banDuplicateClasses>
        </rules>
      </configuration>
    </execution>
  </executions>
  <dependencies>
    <dependency>
      <groupId>org.codehaus.mojo</groupId>
      <artifactId>extra-enforcer-rules</artifactId>
      <version>1.8.0</version>
    </dependency>
  </dependencies>
</plugin>
```

Check the current version of `extra-enforcer-rules` before pinning one. `banDuplicateClasses` needs `ignoreClasses` entries for known harmless overlaps; record the reason beside each.

## Shading checks

After relocating, confirm: reflection by class-name string is relocated, service files under `META-INF/services` are merged (Maven Shade's `ServicesResourceTransformer`), and `module-info` or multi-release entries are not left pointing at original names. List the final jar and search for the original package to prove none remains.

## Reading the class-load log

Lines look like `[0.412s][info][class,load] com.foo.Bar source: file:/app/lib/foo-2.9.0.jar`. A class from a JDK module shows `source: jrt:/java.base`. Classes from a custom loader may show only a jar name, so also grep for the library's other classes to see whether two jars contribute to one package.
