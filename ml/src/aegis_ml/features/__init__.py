from .definitions import BY_NAME, FEATURE_LIST, FEATURE_SET_VERSION, FEATURES, Feature, feature_names

# Compatibility exports for the original M1 scaffold.
FeatureDefinition = Feature
FEATURE_DEFINITIONS = tuple(FEATURES)

__all__ = ["BY_NAME", "FEATURES", "FEATURE_DEFINITIONS", "FEATURE_LIST", "FEATURE_SET_VERSION", "Feature", "FeatureDefinition", "feature_names"]
