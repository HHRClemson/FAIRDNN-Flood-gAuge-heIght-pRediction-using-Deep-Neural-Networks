import numpy as np
import time

import tensorflow as tf
from tensorflow.keras import layers, models, Model


class ReGAN(Model):

    def __init__(self,
                 img_size=512,
                 channels=1,
                 latent_dim=4096,
                 batch_size=128,
                 kernel_size=5,
                 **kwargs):
        super(ReGAN, self).__init__(name="ReGAN", **kwargs)

        self.image_size = img_size
        self.channels = channels
        self.latent_dim = latent_dim
        self.batch_size = batch_size
        self.kernel_size = kernel_size

        # img -> z
        self.encoder: Model = self._create_encoder()
        # [z, l] -> new image
        self.generator: Model = self._create_generator()
        # discriminate the encoder (z) to learn proper encoding
        self.encoder_discriminator: Model = self._create_encoder_discriminator()
        # discriminate the generator (new img) to learn proper new images
        self.image_discriminator: Model = self._create_image_discriminator()

    def _create_encoder(self) -> Model:
        """
        Create an encoder model to translate the image to a latent space which will be the
        input for the generator
        """
        encoder = models.Sequential(name="Encoder")
        encoder.add(layers.InputLayer(
            input_shape=(self.img_size, self.img_size, self.channels)))

        filters = [16, 32, 64, 128]
        for f in filters:
            encoder.add(layers.Conv2D(filters=f, kernel_size=self.kernel_size, padding="same"))
            encoder.add(layers.Activation("relu"))

        encoder.add(layers.Flatten())
        encoder.add(layers.Dense(units=self.latent_dim))

        return encoder

    def _create_generator(self) -> Model:
        """
        Create the generator which generates a new image based on the encoding of the input images
        and their gauge height
        """
        generator = models.Sequential()
        generator.add(layers.Reshape(
            target_shape=[1, 1, self.noise_dim], input_shape=[self.noise_dim]))

        generator.add(layers.Conv2DTranspose(filters=512, kernel_size=4))
        generator.add(layers.Activation("relu"))

        filters = [4, 8, 16, 32, 64, 128, 256]
        for f in reversed(filters):
            generator.add(layers.Conv2D(filters=f, kernel_size=3, padding="same"))
            generator.add(layers.BatchNormalization(momentum=0.7))
            generator.add(layers.Activation("relu"))
            generator.add(layers.UpSampling2D())

        generator.add(layers.Conv2D(filters=self.channels, kernel_size=3, padding="same"))
        generator.add(layers.Activation("sigmoid"))

        return generator

    def _create_encoder_discriminator(self) -> Model:
        """
        Create a discriminator for the encoder to force it to create a proper latent space Z
        """
        pass

    def _create_image_discriminator(self) -> Model:
        """
        Create a discriminator for the generator to force it to generate proper images and also
        judge the gauge height of the generated image
        """
        discriminator = models.Sequential()
        discriminator.add(layers.InputLayer(
            input_shape=(self.img_size, self.img_size, self.channels)))

        filters = [4, 8, 16, 32, 64, 128, 256]
        for f in filters:
            discriminator.add(layers.Conv2D(filters=f, kernel_size=3, padding="same"))
            discriminator.add(layers.BatchNormalization(momentum=0.7))
            discriminator.add(layers.LeakyReLU(0.2))
            discriminator.add(layers.Dropout(0.25))
            discriminator.add(layers.AveragePooling2D())

        discriminator.add(layers.Flatten())
        discriminator.add(layers.Dense(128))
        discriminator.add(layers.LeakyReLU(0.2))
        discriminator.add(layers.Dense(1))

        return discriminator

    def train(self, dataset, epochs, batch_size):
        generated_images = []

        for epoch in range(epochs):
            start = time.time()

            next_batch = []
            min_gen_loss = 999999
            min_disc_loss = 999999

            for i in range(len(dataset)):
                next_batch.append(dataset[i])
                if i % batch_size == 0:
                    gen_loss, disc_loss = self.train_step(np.array(next_batch))
                    min_gen_loss = min(min_gen_loss, gen_loss)
                    min_disc_loss = min(min_disc_loss, disc_loss)
                    next_batch = []

            # generate 10 times pictures based on the generator trained to this epoch
            # to visualize the improvements and find the sweet epoch point
            if epoch % (epochs / 10) == 0:
                generated_images.append(self.call(tf.random.normal([16, self.noise_dim])))

            print('Time for epoch {e}/{ne} is {t} sec. Generator loss: {gl}, Discriminiator loss: {dl}'
                  .format(e=epoch + 1,
                          ne=epochs,
                          t=time.time() - start,
                          gl=min_gen_loss,
                          dl=min_disc_loss))

        return generated_images

    @tf.function
    def train_step(self, images):
        noise = tf.random.normal([self.batch_size, self.noise_dim])

        with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
            generated_images = self.generator(noise, training=True)

            real_output = self.discriminator(images, training=True)
            fake_output = self.discriminator(generated_images, training=True)

            generator_loss = self.gen_loss(fake_output)
            discriminator_loss = self.disc_loss(real_output, fake_output)

        gen_grads = gen_tape.gradient(generator_loss, self.generator.trainable_variables)
        self.gen_optimizer.apply_gradients(zip(gen_grads, self.generator.trainable_variables))

        disc_grads = disc_tape.gradient(discriminator_loss, self.discriminator.trainable_variables)
        self.disc_optimizer.apply_gradients(zip(disc_grads, self.discriminator.trainable_variables))
        return generator_loss, discriminator_loss

    def call(self, inputs, training=None, mask=None):
        pass

    def get_config(self):
        config = super(ReGAN, self).get_config()
        config.update({
            "img_size": self.image_size,
            "channels": self.channels,
            "latent_dim": self.latent_dim,
            "batch_size": self.batch_size,
            "kernel_size": self.kernel_size
        })
        return config

    def summary(self, line_length=None, positions=None, print_fn=None):
        self.encoder.summary(line_length, positions, print_fn)
        self.encoder_discriminator.summary(line_length, positions, print_fn)
        self.generator.summary(line_length, positions, print_fn)
        self.image_discriminator.summary(line_length, positions, print_fn)


if __name__ == "__main__":
    gan = ReGAN()
    gan.summary()
