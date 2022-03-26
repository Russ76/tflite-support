# Copyright 2022 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Audio classifier task."""

import dataclasses

from tensorflow_lite_support.python.task.core.proto import base_options_pb2
from tensorflow_lite_support.python.task.processor.proto import embedding_options_pb2
from tensorflow_lite_support.python.task.processor.proto import embeddings_pb2
from tensorflow_lite_support.python.task.audio.core import tensor_audio
from tensorflow_lite_support.python.task.audio.core import audio_record
from tensorflow_lite_support.python.task.audio.core.pybinds import _pywrap_audio_buffer
from tensorflow_lite_support.python.task.audio.pybinds import _pywrap_audio_embedder
from tensorflow_lite_support.python.task.audio.pybinds import audio_embedder_options_pb2

_CppAudioFormat = _pywrap_audio_buffer.AudioFormat
_CppAudioBuffer = _pywrap_audio_buffer.AudioBuffer
_ProtoAudioEmbedderOptions = audio_embedder_options_pb2.AudioEmbedderOptions
_CppAudioEmbedder = _pywrap_audio_embedder.AudioEmbedder
_BaseOptions = base_options_pb2.BaseOptions
_EmbeddingOptions = embedding_options_pb2.EmbeddingOptions


@dataclasses.dataclass
class AudioEmbedderOptions:
  """Options for the audio embedder task."""
  base_options: _BaseOptions
  embedding_options: _EmbeddingOptions = _EmbeddingOptions()


class AudioEmbedder(object):
  """Class that performs dense feature vector extraction on audio."""

  def __init__(self, options: AudioEmbedderOptions,
               cpp_embedder: _CppAudioEmbedder) -> None:
    # Creates the object of C++ AudioEmbedder class.
    self._options = options
    self._embedder = cpp_embedder

  @classmethod
  def create_from_file(cls, file_path: str) -> "AudioEmbedder":
    """Creates the `AudioEmbedder` object from a TensorFlow Lite model.
    Args:
      file_path: Path to the model.
    Returns:
      `AudioEmbedder` object that's created from `options`.
    Raises:
      status.StatusNotOk if failed to create `AudioEmbedder` object from the
      provided file such as invalid file.
    """
    # TODO(b/220931229): Raise RuntimeError instead of status.StatusNotOk.
    # Need to import the module to catch this error:
    # `from pybind11_abseil import status`
    # see https://github.com/pybind/pybind11_abseil#abslstatusor.
    base_options = _BaseOptions(file_name=file_path)
    options = AudioEmbedderOptions(base_options=base_options)
    return cls.create_from_options(options)

  @classmethod
  def create_from_options(cls, options: AudioEmbedderOptions) -> "AudioEmbedder":
    """Creates the `AudioEmbedder` object from audio embedder options.
    Args:
      options: Options for the audio embedder task.
    Returns:
      `AudioEmbedder` object that's created from `options`.
    Raises:
      status.StatusNotOk if failed to create `AudioEmbedder` object from
      `AudioEmbedderOptions` such as missing the model.
    """
    # TODO(b/220931229): Raise RuntimeError instead of status.StatusNotOk.
    # Need to import the module to catch this error:
    # `from pybind11_abseil import status`
    # see https://github.com/pybind/pybind11_abseil#abslstatusor.
    embedder = _CppAudioEmbedder.create_from_options(options.base_options,
                                                     options.embedding_options)
    return cls(options, embedder)

  def create_input_tensor_audio(self) -> tensor_audio.TensorAudio:
    """Creates a TensorAudio instance to store the audio input.
    Returns:
        A TensorAudio instance.
    """
    return tensor_audio.TensorAudio(audio_format=self.required_audio_format,
                                    buffer_size=self.required_input_buffer_size)

  def create_audio_record(self) -> audio_record.AudioRecord:
    """Creates an AudioRecord instance to record audio.
    Returns:
        An AudioRecord instance.
    """
    return audio_record.AudioRecord(self.required_audio_format.channels,
                                    self.required_audio_format.sample_rate,
                                    self.required_input_buffer_size)

  def embed(
      self,
      audio: tensor_audio.TensorAudio
  ) -> embeddings_pb2.EmbeddingResult:
    """Performs actual feature vector extraction on the provided audio.
    Args:
      audio: Tensor audio, used to extract the feature vectors.
    Returns:
      embedding result.
    Raises:
      status.StatusNotOk if failed to get the embedding vector. Need to import
        the module to catch this error: `from pybind11_abseil import status`,
        see https://github.com/pybind/pybind11_abseil#abslstatusor.
    """
    return self._embedder.embed(_CppAudioBuffer(audio.buffer,
                                                audio.buffer_size,
                                                audio.format))

  def cosine_similarity(self, u: embeddings_pb2.FeatureVector,
                        v: embeddings_pb2.FeatureVector) -> float:
    """Computes cosine similarity [1] between two feature vectors."""
    return self._embedder.cosine_similarity(u, v)

  def get_embedding_dimension(self, output_index: int) -> int:
    """Gets the dimensionality of the embedding output.
    Args:
      output_index: The output index of output layer.
    Returns:
      Dimensionality of the embedding output by the output_index'th output
      layer. Returns -1 if `output_index` is out of bounds.
    """
    return self._embedder.get_embedding_dimension(output_index)

  @property
  def number_of_output_layers(self) -> int:
    """Gets the number of output layers of the model."""
    return self._embedder.get_number_of_output_layers()

  @property
  def required_input_buffer_size(self) -> int:
    """Gets the required input buffer size for the model."""
    return self._embedder.get_required_input_buffer_size()

  @property
  def required_audio_format(self) -> _CppAudioFormat:
    """Gets the required audio format for the model."""
    return self._embedder.get_required_audio_format()
