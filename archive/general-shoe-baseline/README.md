# General shoes dataset

Source: Roboflow Universe, Shoe Detection v2

License: CC BY 4.0

Source URL: https://universe.roboflow.com/robotics-lo9nk/shoe-detection-lmpo9/dataset/2

Preparation: merged both source classes into `shoe`, converted polygon labels to bounding boxes, and reassigned splits by pre-augmentation source ID to prevent source-image leakage across train, validation, and test.
