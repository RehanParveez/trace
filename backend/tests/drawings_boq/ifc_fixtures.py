from __future__ import annotations

import ifcopenshell.api as api
import numpy as np

def _matrix(x_m: float, y_m: float, z_m: float) -> np.ndarray:
  return np.array([[1, 0, 0, x_m], [0, 1, 0, y_m], [0, 0, 1, z_m], [0, 0, 0, 1]], dtype=float)


def build_villa_ifc(path: str) -> None:
  f = api.run("project.create_file", version="IFC4")
  project = api.run("root.create_entity", f, ifc_class="IfcProject", name="Villa")
  api.run("unit.assign_unit", f, length={"is_metric": True, "raw": "MILLIMETERS"})
  model_ctx = api.run("context.add_context", f, context_type="Model")
  body = api.run(
    "context.add_context", f, context_type="Model", context_identifier="Body",
    target_view="MODEL_VIEW", parent=model_ctx,
  )

  site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Site")
  building = api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Building")
  ground = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Ground")
  ground.Elevation = 0.0
  first = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="First")
  first.Elevation = 3000.0
  api.run("aggregate.assign_object", f, products=[site], relating_object=project)
  api.run("aggregate.assign_object", f, products=[building], relating_object=site)
  api.run("aggregate.assign_object", f, products=[ground, first], relating_object=building)

  def make(ifc_class: str, name: str, storey, **kwargs):
    element = api.run("root.create_entity", f, ifc_class=ifc_class, name=name, **kwargs)
    api.run("spatial.assign_container", f, products=[element], relating_structure=storey)
    return element

  def qto(element, qto_name: str, values: dict) -> None:
    q = api.run("pset.add_qto", f, product=element, name=qto_name)
    api.run("pset.edit_qto", f, qto=q, properties=values)

  wall_a = make("IfcWall", "Wall A", ground)
  rep = api.run("geometry.add_wall_representation", f, context=body, length=5, height=3, thickness=0.23)
  api.run("geometry.assign_representation", f, product=wall_a, representation=rep)
  api.run("geometry.edit_object_placement", f, product=wall_a, matrix=_matrix(1, 2, 0))
  qto(wall_a, "Qto_WallBaseQuantities", {"Length": 5000.0, "Height": 3000.0, "Width": 230.0, "NetVolume": 3.45})
  pset = api.run("pset.add_pset", f, product=wall_a, name="Pset_WallCommon")
  api.run("pset.edit_pset", f, pset=pset, properties={"IsExternal": True})
  brick = api.run("material.add_material", f, name="Brick 230")
  api.run("material.assign_material", f, products=[wall_a], material=brick)

  wall_b = make("IfcWall", "Wall B", ground)
  rep = api.run("geometry.add_wall_representation", f, context=body, length=4, height=3, thickness=0.2)
  api.run("geometry.assign_representation", f, product=wall_b, representation=rep)

  make("IfcWall", "Shear 1", ground, predefined_type="SHEAR")

  slab = make("IfcSlab", "Slab 1", first, predefined_type="FLOOR")
  rep = api.run(
    "geometry.add_slab_representation", f, context=body, depth=0.125,
    polyline=[(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)],
  )
  api.run("geometry.assign_representation", f, product=slab, representation=rep)
  api.run("geometry.edit_object_placement", f, product=slab, matrix=_matrix(0, 0, 3))

  column = make("IfcColumn", "Column C1", ground)
  profile = f.create_entity("IfcRectangleProfileDef", ProfileType="AREA", XDim=300.0, YDim=300.0)
  rep = api.run("geometry.add_profile_representation", f, context=body, profile=profile, depth=3.0)
  api.run("geometry.assign_representation", f, product=column, representation=rep)

  door = make("IfcDoor", "Door D1", ground)
  door.OverallWidth, door.OverallHeight = 900.0, 2100.0
  window = make("IfcWindow", "Window W1", ground)
  window.OverallWidth, window.OverallHeight = 1200.0, 1200.0

  make("IfcCovering", "Tiles", ground, predefined_type="FLOORING")
  make("IfcBuildingElementProxy", "Beam B1", ground)
  make("IfcBuildingElementProxy", "Composite deck", ground)

  for idx, length in enumerate((3000.0, 1500.0), start=1):
    pipe = make("IfcPipeSegment", f"Pipe {idx}", ground)
    qto(pipe, "Qto_PipeSegmentBaseQuantities", {"Length": length})
  make("IfcSanitaryTerminal", "WC 1", ground)
  make("IfcLightFixture", "Light 1", ground)

  make("IfcReinforcingBar", "Bar 1", ground)
  make("IfcOpeningElement", "Opening 1", ground)

  f.write(path)

def build_ifc2x3_minimal(path: str) -> None:
  import ifcopenshell.api.owner.settings as owner_settings

  f = api.run("project.create_file", version="IFC2X3")
  org = f.create_entity("IfcOrganization", Name="Test")
  user = f.create_entity("IfcPersonAndOrganization", ThePerson=f.create_entity("IfcPerson"), TheOrganization=org)
  application = f.create_entity(
    "IfcApplication", ApplicationDeveloper=org, Version="1", ApplicationFullName="Test", ApplicationIdentifier="test",
  )
  owner_settings.get_user = lambda ifc: user
  owner_settings.get_application = lambda ifc: application
  project = api.run("root.create_entity", f, ifc_class="IfcProject", name="Old")
  api.run("unit.assign_unit", f, length={"is_metric": True, "raw": "METERS"})
  site = api.run("root.create_entity", f, ifc_class="IfcSite", name="S")
  building = api.run("root.create_entity", f, ifc_class="IfcBuilding", name="B")
  storey = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="L0")
  storey.Elevation = 0.0
  api.run("aggregate.assign_object", f, products=[site], relating_object=project)
  api.run("aggregate.assign_object", f, products=[building], relating_object=site)
  api.run("aggregate.assign_object", f, products=[storey], relating_object=building)
  wall = api.run("root.create_entity", f, ifc_class="IfcWallStandardCase", name="W")
  api.run("spatial.assign_container", f, products=[wall], relating_structure=storey)
  q = api.run("pset.add_qto", f, product=wall, name="BaseQuantities")
  api.run("pset.edit_qto", f, qto=q, properties={"NetVolume": 2.0, "Length": 4.0, "Height": 2.5, "Width": 0.2})
  f.write(path)