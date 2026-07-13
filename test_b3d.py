"""Quick smoke test: read a .b3d file and print metadata."""
import sys
from pathlib import Path

import nimblephysics as nimble

B3D_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "movedb-core/tests/data/P010_split0.b3d"

print(f"Loading {B3D_PATH} ({B3D_PATH.stat().st_size / 1e6:.0f} MB)...")
subject = nimble.biomechanics.SubjectOnDisk(str(B3D_PATH))

print(f"  Mass:      {subject.getMassKg()} kg")
print(f"  Height:    {subject.getHeightM()} m")
print(f"  Age:       {subject.getAgeYears()}")
print(f"  Sex:       {subject.getBiologicalSex()}")
print(f"  DOFs:      {subject.getNumDofs()}")
print(f"  Trials:    {subject.getNumTrials()}")
print(f"  Passes:    {subject.getNumProcessingPasses()}")
print(f"  Quality:   {subject.getQuality()}")
print(f"  Tags:      {list(subject.getSubjectTags())}")
print(f"  Href:      {subject.getHref()}")

skel = subject.readSkel(processingPass=0, ignoreGeometry=True)
dof_names = [skel.getDofByIndex(i).getName() for i in range(skel.getNumDofs())]
print(f"  First 5 DOFs: {dof_names[:5]}")

for t in range(min(subject.getNumTrials(), 3)):
    name = subject.getTrialName(t)
    frames = subject.getTrialLength(t)
    dt = subject.getTrialTimestep(t)
    print(f"  Trial {t}: {name} ({frames} frames, {dt}s timestep)")

print("\nDone.")
