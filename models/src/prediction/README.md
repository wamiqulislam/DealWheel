# src/prediction

Not built yet. This is where inference code will live once a trained
model exists -- e.g. a function that takes a raw listing (or a
partial one, for a "what should I list my car at" tool) and runs it
through the same src/preprocessing + src/features pipeline before
scoring it with the model.

Reuse `src/features/build_features.py` for this rather than
re-deriving features by hand, so a prediction-time listing gets
exactly the same transformations as training-time listings did.
